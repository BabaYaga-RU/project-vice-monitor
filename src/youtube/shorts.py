"""Render deterministic, narrated vertical videos from published article data.

The renderer deliberately uses only facts and wording already present in the
article. Speech is local eSpeak NG; no extra AI request or remote TTS service is
used. The returned MP4 is shared by downstream publishers.
"""

from __future__ import annotations

import json
import os
import random
import re
import shlex
import shutil
import subprocess
import urllib.request
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH, HEIGHT, FPS = 1080, 1920, 30
ROOT = Path(__file__).resolve().parents[2]
MUSIC_DIR = ROOT / "assets" / "audio" / "shorts"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    options = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf"]
    )
    for candidate in options:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words, lines, line = str(text).split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _article_script(article: dict) -> list[tuple[str, str]]:
    """Return concise (screen text, narration) beats from the supplied article."""
    title = re.sub(r"\s+", " ", str(article.get("title", "GTA and Rockstar news"))).strip()
    description = re.sub(r"\s+", " ", str(article.get("description", ""))).strip()
    source_sentences: list[str] = []
    if description:
        source_sentences.extend(re.split(r"(?<=[.!?])\s+", description))
    for section in article.get("sections", []):
        for paragraph in section.get("paragraphs", []):
            source_sentences.extend(re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", str(paragraph)).strip()))

    beats: list[tuple[str, str]] = [(title, f"GTA update. {title}")]
    remaining = 15
    used = {title.casefold()}
    for sentence in source_sentences:
        sentence = sentence.strip()
        if not sentence or sentence.casefold() in used:
            continue
        words = sentence.split()
        if len(words) > remaining:
            words = words[:remaining]
            sentence = " ".join(words).rstrip(" ,;:-") + "."
        if len(words) < 4:
            continue
        beats.append((sentence, sentence))
        remaining -= len(words)
        used.add(sentence.casefold())
        if remaining <= 0 or len(beats) >= 5:
            break

    cta = "Read the full story on Macca Blog."
    beats.append(("FULL STORY  •  MACCA BLOG", cta))
    # Each short phrase gets its own cut/card and matching spoken segment.
    # At the selected local TTS rate this usually changes visuals every ~2s.
    phrase_beats: list[tuple[str, str]] = []
    for screen, narration in beats:
        words = narration.split()
        for start in range(0, len(words), 6):
            phrase = " ".join(words[start:start + 6])
            phrase_beats.append((phrase, phrase))
    return phrase_beats


def _load_background(article: dict, work: Path) -> Image.Image:
    candidates = [article.get("thumbnail", ""), *[item.get("url", "") for item in article.get("inlineImages", [])]]
    for index, url in enumerate(candidates):
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MaccaBlogPublisher/1.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(12 * 1024 * 1024)
            candidate = work / f"article-background-{index}.img"
            candidate.write_bytes(data)
            with Image.open(candidate) as image:
                return image.convert("RGB")
        except Exception:
            continue
    fallback = ROOT / "images" / "macca-blog-banner.jpg"
    with Image.open(fallback) as image:
        return image.convert("RGB")


def _render_card(path: Path, background: Image.Image, headline: str, beat_index: int, total: int) -> None:
    # Small per-beat crop changes complement FFmpeg's gentle Ken Burns movement.
    x_shift = ((beat_index * 73) % 150) - 75
    y_shift = ((beat_index * 41) % 100) - 50
    image = ImageOps.fit(
        background,
        (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(max(0.05, min(0.95, 0.5 + x_shift / 1200)), max(0.05, min(0.95, 0.5 + y_shift / 1800))),
    ).convert("RGBA")
    shade = Image.new("RGBA", image.size, (8, 5, 17, 88))
    image = Image.alpha_composite(image, shade)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((48, 255, 1032, 1510), radius=44, fill=(14, 9, 27, 205), outline=(255, 104, 173, 210), width=4)
    draw.text((96, 322), "MACCA THE GATOR  •  GTA & ROCKSTAR", font=_font(29, True), fill=(77, 224, 237, 255))
    draw.rounded_rectangle((96, 390, 260, 400), radius=5, fill=(255, 104, 173, 255))
    words = headline.split()
    screen_text = " ".join(words[:8]) + ("…" if len(words) > 8 else "")
    font = _font(64 if len(screen_text) < 90 else 53, True)
    lines = _wrap(draw, screen_text, font, 860)
    if len(lines) > 8:
        lines = lines[:7] + [lines[7].rstrip(" ,;:-") + "…"]
    total_height = len(lines) * (font.size + 20)
    y = 890 - total_height // 2
    for line in lines:
        draw.text((96, y), line, font=font, fill=(255, 245, 240, 255), stroke_width=2, stroke_fill=(10, 7, 20, 220))
        y += font.size + 20
    draw.text((96, 1370), f"{beat_index + 1:02d}  /  {total:02d}", font=_font(27, True), fill=(255, 154, 107, 255))
    if beat_index == total - 1:
        draw.text((96, 1370), "MACCA BLOG  →  FULL STORY", font=_font(31, True), fill=(77, 224, 237, 255))
    image.convert("RGB").save(path, quality=92)


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", " ")


def _write_subtitles(path: Path, beats: list[tuple[str, str]], durations: list[float]) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,54,&H00FFFFFF,&H0000F3FF,&H00130C20,&HCC130C20,1,0,0,0,100,100,0,0,1,4,1,2,70,70,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    elapsed = 0.0
    for (_, caption), duration in zip(beats, durations):
        words = caption.split()
        chunks = [" ".join(words[index:index + 6]) for index in range(0, len(words), 6)] or [caption]
        total_words = max(1, len(words))
        cursor = elapsed
        for chunk in chunks:
            chunk_duration = duration * len(chunk.split()) / total_words
            end = cursor + chunk_duration
            events.append(f"Dialogue: 0,{_ass_time(cursor)},{_ass_time(end)},Caption,,0,0,0,,{_escape_ass(chunk)}")
            cursor = end
        elapsed = end
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def _music_track() -> Path | None:
    explicit = os.environ.get("SHORTS_MUSIC_PATH")
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return candidate
    tracks = sorted(p for p in MUSIC_DIR.rglob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}) if MUSIC_DIR.exists() else []
    return random.choice(tracks) if tracks else None


def _create_narrated_short(article: dict, output: str | Path, workdir: str | Path) -> Path:
    """Render an H.264/AAC 1080x1920 video with local TTS and burned captions."""
    ffmpeg = shutil.which("ffmpeg")
    tts = shutil.which("espeak-ng") or shutil.which("espeak")
    tts_command = shlex.split(os.environ.get("SHORTS_TTS_COMMAND", ""), posix=os.name != "nt")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render social videos.")
    if not tts and not tts_command:
        raise RuntimeError("Install espeak-ng to render the local narrated video.")

    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    beats = _article_script(article)
    background = _load_background(article, work)
    durations: list[float] = []
    audio_files: list[Path] = []
    video_files: list[Path] = []
    for index, (_, narration) in enumerate(beats):
        audio_path = work / f"voice-{index:02d}.wav"
        subprocess.run([*(tts_command or [tts]), "-v", os.environ.get("SHORTS_TTS_VOICE", "en-us"), "-s", "165", "-w", str(audio_path), narration], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # A short tail prevents consonants from being cut between visual beats.
        duration = _audio_duration(audio_path) + 0.12
        durations.append(duration)
        audio_files.append(audio_path)
        card = work / f"scene-{index:02d}.jpg"
        _render_card(card, background, beats[index][0], index, len(beats))
        clip = work / f"scene-{index:02d}.mp4"
        frames = max(1, round(duration * FPS))
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(card), "-t", f"{duration:.3f}",
            "-vf", f"zoompan=z='min(zoom+0.00045,1.035)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-movflags", "+faststart", str(clip),
        ], check=True)
        video_files.append(clip)
    tts_name = Path(tts).name if tts else Path(tts_command[0]).name
    print(f"Generated {len(audio_files)} narration clips with {tts_name}.")

    joined_audio = work / "voice.wav"
    with wave.open(str(audio_files[0]), "rb") as first:
        params = first.getparams()
        with wave.open(str(joined_audio), "wb") as combined:
            combined.setparams(params)
            for audio_path in audio_files:
                with wave.open(str(audio_path), "rb") as audio:
                    if audio.getparams()[:3] != params[:3]:
                        raise RuntimeError("TTS returned inconsistent audio formats between narration beats.")
                    combined.writeframes(audio.readframes(audio.getnframes()))
                    combined.writeframes(b"\0" * round(params.framerate * 0.12) * params.nchannels * params.sampwidth)

    listing = work / "clips.txt"
    listing.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in video_files) + "\n", encoding="utf-8")
    subtitles = work / "captions.ass"
    _write_subtitles(subtitles, beats, durations)
    print(f"Burning synchronized captions from {subtitles.name} into {len(beats)} visual beats.")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    music = _music_track()
    caption_filter_path = str(subtitles).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(joined_audio)]
    if music:
        command += ["-stream_loop", "-1", "-i", str(music)]
        audio_filter = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];[2:a]loudnorm=I=-32:TP=-8:LRA=7[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    else:
        audio_filter = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    command += ["-filter_complex", audio_filter, "-vf", f"ass='{caption_filter_path}'", "-map", "0:v:0", "-map", "[aout]", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(output_path)]
    subprocess.run(command, check=True)
    duration = sum(durations)
    if not 15 <= duration <= 25:
        # The words are capped to keep typical output within range; reject outliers
        # rather than unexpectedly upload a video outside the requested duration.
        raise RuntimeError(f"Narrated video duration is {duration:.1f}s; expected 15-25s. Reduce article summary text.")
    return output_path


def create_legacy_short(article: dict, output: str | Path, workdir: str | Path) -> Path:
    """Retained 7-second-per-card renderer for explicit rollback/diagnostics."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render social videos.")
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    background = _load_background(article, work)
    slides: list[tuple[str, str]] = [("THE LATEST STORY", str(article.get("title", "GTA & Rockstar News")))]
    description = str(article.get("description", "")).strip()
    if description:
        slides.append(("WHAT HAPPENED", description))
    for section in article.get("sections", [])[:2]:
        paragraphs = section.get("paragraphs", [])
        summary = " ".join(str(value).strip() for value in paragraphs[:1] if str(value).strip())
        if summary:
            slides.append((str(section.get("heading", "STORY DETAILS")), summary))
    if len(slides) == 1 and article.get("sourceUrl"):
        slides.append(("SOURCE", str(article["sourceUrl"])))
    slides = slides[:4]
    listing = work / "legacy-slides.txt"
    cards = []
    for index, (heading, text) in enumerate(slides, 1):
        card = work / f"legacy-slide-{index:02d}.jpg"
        image = ImageOps.fit(background, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS).convert("RGBA")
        image = Image.alpha_composite(image, Image.new("RGBA", image.size, (12, 8, 24, 135)))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rounded_rectangle((54, 340, 1026, 1530), radius=48, fill=(14, 10, 27, 205), outline=(255, 104, 173, 210), width=4)
        draw.text((104, 410), "MACCA THE GATOR  |  GTA & ROCKSTAR", font=_font(34, True), fill=(77, 224, 237, 255))
        draw.text((104, 545), heading.upper()[:48], font=_font(31, True), fill=(255, 154, 107, 255))
        font = _font(56 if len(text) < 180 else 48, True)
        lines = _wrap(draw, text, font, 860)
        if len(lines) > 9:
            lines = lines[:8] + [lines[8][:max(1, len(lines[8]) - 3)] + "..."]
        y = 625
        for line in lines:
            draw.text((104, y), line, font=font, fill=(255, 242, 236, 255), stroke_width=1, stroke_fill=(12, 8, 24, 255))
            y += 76 if font.size > 50 else 66
        draw.text((104, 1430), "READ THE FULL STORY", font=_font(30, True), fill=(77, 224, 237, 255))
        draw.text((104, 1480), f"{index:02d} / {len(slides):02d}   |   MACCA-LAB.ONRENDER.COM/BLOG", font=_font(22, True), fill=(225, 204, 224, 255))
        image.convert("RGB").save(card, quality=92)
        cards.append(card)
    with listing.open("w", encoding="utf-8") as file:
        for card in cards:
            file.write(f"file '{card.as_posix()}'\n")
            file.write("duration 7\n")
        file.write(f"file '{cards[-1].as_posix()}'\n")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-vf", f"fps={FPS},scale={WIDTH}:{HEIGHT},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-movflags", "+faststart", "-t", str(len(slides) * 7), str(output_path)], check=True)
    return output_path


def create_short(article: dict, output: str | Path, workdir: str | Path) -> Path:
    """Default to narrated video; retain the old renderer as an opt-in rollback."""
    if os.environ.get("SHORTS_RENDERER", "narrated").lower() == "legacy":
        return create_legacy_short(article, output, workdir)
    return _create_narrated_short(article, output, workdir)


def main() -> None:
    article = json.loads(os.environ["ARTICLE_JSON"])
    create_short(article, os.environ["OUTPUT_VIDEO"], os.environ["WORK_DIR"])


if __name__ == "__main__":
    main()
