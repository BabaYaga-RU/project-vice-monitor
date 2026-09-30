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
MAX_SLIDES = 4
MIN_DURATION = 15.0
MAX_DURATION = 20.0
CTA_TEXT = "Full story \u2192 link in bio."


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
    """Wrap at word boundaries, balancing lines and avoiding orphan words."""
    words = str(text).split()
    if not words:
        return []

    expanded: list[str] = []
    for word in words:
        while draw.textbbox((0, 0), word, font=font)[2] > width and len(word) > 1:
            split_at = max(
                (index for index in range(1, len(word))
                 if draw.textbbox((0, 0), word[:index] + "-", font=font)[2] <= width),
                default=0,
            )
            if not split_at:
                break
            expanded.append(word[:split_at] + "-")
            word = word[split_at:]
        expanded.append(word)

    def text_width(value: str) -> int:
        box = draw.textbbox((0, 0), value, font=font)
        return box[2] - box[0]

    count = len(expanded)
    costs = [float("inf")] * (count + 1)
    next_break = [count] * count
    costs[count] = 0.0
    for start in range(count - 1, -1, -1):
        for end in range(start + 1, count + 1):
            line = " ".join(expanded[start:end])
            line_width = text_width(line)
            if line_width > width:
                break
            slack = width - line_width
            is_last = end == count
            cost = (slack / max(width, 1)) ** 2 * (0.42 if is_last else 1.0)
            if end - start == 1 and count > 2:
                cost += 0.65
            if is_last and end - start == 1 and count > 3:
                cost += 1.2
            total_cost = cost + costs[end]
            if total_cost < costs[start]:
                costs[start] = total_cost
                next_break[start] = end

    lines: list[str] = []
    start = 0
    while start < count:
        end = next_break[start]
        if end <= start:
            end = start + 1
        lines.append(" ".join(expanded[start:end]))
        start = end
    return lines


def _layout_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    *,
    max_font_size: int = 86,
    min_font_size: int = 26,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """Choose the largest readable font whose balanced lines fit the card."""
    value = re.sub(r"\s+", " ", str(text)).strip()
    if not value:
        raise ValueError("A video card cannot contain empty text.")
    for size in range(max_font_size, min_font_size - 1, -2):
        font = _font(size, True)
        lines = _wrap(draw, value, font, max_width)
        line_height = round(size * 1.22)
        if lines and len(lines) * line_height <= max_height and all(
            draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0] <= max_width
            for line in lines
        ):
            return font, lines, line_height
    raise ValueError("Card text cannot fit inside the safe area, even at the minimum font size.")


_FRAGMENT_ENDINGS = {
    "a", "an", "and", "as", "at", "because", "but", "by", "for", "from", "if",
    "in", "into", "is", "of", "on", "or", "that", "the", "to", "was", "were",
    "which", "while", "with", "who", "will", "would", "won't", "hasn't", "haven't",
}


def _complete_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(text)).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        words = sentence.split()
        if len(words) < 7 or not re.search(r"[.!?][\"'\u2019)]*$", sentence):
            continue
        if words[-1].rstrip(".!?\"'\u2019)").lower() in _FRAGMENT_ENDINGS:
            continue
        result.append(sentence)
    return result


def _article_script(article: dict) -> list[tuple[str, str]]:
    """Make no more than four complete, useful cards from existing article text."""
    title = re.sub(r"\s+", " ", str(article.get("title", "GTA and Rockstar news"))).strip()
    source_sentences = _complete_sentences(article.get("description", ""))
    for section in article.get("sections", []):
        for paragraph in section.get("paragraphs", []):
            source_sentences.extend(_complete_sentences(paragraph))

    selected: list[str] = []
    for sentence in source_sentences:
        words = set(re.sub(r"\W+", " ", sentence.casefold()).split())
        if not words:
            continue
        duplicate = False
        for previous in selected:
            previous_words = set(re.sub(r"\W+", " ", previous.casefold()).split())
            shared = len(words & previous_words)
            if shared >= 8 and shared / min(len(words), len(previous_words)) >= 0.48:
                duplicate = True
                break
        if not duplicate:
            selected.append(sentence)
        if len(selected) >= 2:
            break

    beats: list[tuple[str, str]] = [(title, "Rockstar fans, here is the latest story.")]
    beats.extend((sentence, sentence) for sentence in selected)
    beats.append((CTA_TEXT, CTA_TEXT))
    if len(beats) > MAX_SLIDES:
        raise RuntimeError(f"The shared renderer produced more than {MAX_SLIDES} slides.")
    return beats

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
    image = ImageOps.fit(
        background,
        (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    ).convert("RGBA")
    image = Image.alpha_composite(image, Image.new("RGBA", image.size, (8, 5, 17, 112)))
    draw = ImageDraw.Draw(image, "RGBA")

    draw.text((76, 235), "MACCA THE GATOR  |  GTA & ROCKSTAR", font=_font(28, True), fill=(77, 224, 237, 255))
    draw.rounded_rectangle((76, 300, 1004, 309), radius=5, fill=(52, 43, 64, 255))
    progress_right = 76 + round(928 * (beat_index + 1) / max(total, 1))
    draw.rounded_rectangle((76, 300, progress_right, 309), radius=5, fill=(255, 104, 173, 255))

    font, lines, line_height = _layout_text(draw, headline, 820, 780, max_font_size=86, min_font_size=26)
    text_height = len(lines) * line_height
    panel_height = max(380, text_height + 144)
    panel_top = 965 - panel_height // 2
    panel_bottom = panel_top + panel_height
    draw.rounded_rectangle(
        (54, panel_top, 1026, panel_bottom), radius=42,
        fill=(14, 9, 27, 226), outline=(255, 104, 173, 205), width=3,
    )
    draw.rounded_rectangle((91, panel_top + 46, 101, panel_top + 116), radius=5, fill=(77, 224, 237, 255))

    y = panel_top + (panel_height - text_height) // 2
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font, stroke_width=1)
        line_width = box[2] - box[0]
        x = (WIDTH - line_width) // 2
        draw.text((x, y), line, font=font, fill=(255, 247, 242, 255), stroke_width=1, stroke_fill=(10, 7, 20, 220))
        y += line_height

    footer = f"MACCA BLOG                                      {beat_index + 1:02d} / {total:02d}"
    draw.text((76, 1570), footer, font=_font(25, True), fill=(230, 215, 232, 255))
    image.convert("RGB").save(path, quality=92)

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
    """Render a 15-20 second H.264/AAC video with up to four readable cards."""
    ffmpeg = shutil.which("ffmpeg")
    tts = shutil.which("espeak-ng") or shutil.which("espeak")
    tts_command = shlex.split(os.environ.get("SHORTS_TTS_COMMAND", ""), posix=os.name != "nt")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render social videos.")
    if not tts and not tts_command:
        raise RuntimeError("Install espeak-ng to render the local narrated video.")
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe is required to validate rendered social videos.")

    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    beats = _article_script(article)
    background = _load_background(article, work)
    audio_files: list[Path] = []
    speech_durations: list[float] = []
    card_durations: list[float] = []
    voice_rate = 180

    while True:
        audio_files = []
        speech_durations = []
        for index, (_, narration) in enumerate(beats):
            audio_path = work / f"voice-{index:02d}.wav"
            subprocess.run(
                [*(tts_command or [tts]), "-v", os.environ.get("SHORTS_TTS_VOICE", "en-us"), "-s", str(voice_rate), "-w", str(audio_path), narration],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            audio_files.append(audio_path)
            speech_durations.append(_audio_duration(audio_path))

        # Keep each card readable; if the story still runs long, remove the
        # second supporting fact as a whole sentence rather than cutting it.
        card_durations = [max(duration + 0.14, 2.8) for duration in speech_durations]
        # Add a small frame-boundary margin so the encoded MP4 probes at 15s or longer.
        total_duration = max(MIN_DURATION + 0.2, sum(card_durations))
        if total_duration <= MAX_DURATION:
            card_durations[-1] += total_duration - sum(card_durations)
            break
        if len(beats) == MAX_SLIDES:
            # Preserve the hook, main fact, and CTA; remove only the optional context card.
            beats = beats[:2] + beats[-1:]
            continue
        if voice_rate < 210:
            voice_rate += 10
            continue
        raise RuntimeError(f"Narrated video would exceed {MAX_DURATION:.0f} seconds without cutting a complete fact.")

    tts_name = Path(tts).name if tts else Path(tts_command[0]).name
    print(f"Generated {len(audio_files)} narration clips with {tts_name} at {voice_rate} wpm.")
    print(f"Rendering {len(beats)} complete visual cards; duplicated lower captions and Ken Burns movement are disabled.")

    video_files: list[Path] = []
    for index, (headline, _) in enumerate(beats):
        card = work / f"scene-{index:02d}.jpg"
        _render_card(card, background, headline, index, len(beats))
        clip = work / f"scene-{index:02d}.mp4"
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(card),
            "-t", f"{card_durations[index]:.3f}", "-vf", f"fps={FPS},format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
            "-movflags", "+faststart", str(clip),
        ], check=True)
        video_files.append(clip)

    joined_audio = work / "voice.wav"
    with wave.open(str(audio_files[0]), "rb") as first:
        params = first.getparams()
        with wave.open(str(joined_audio), "wb") as combined:
            combined.setparams(params)
            for audio_path, card_duration in zip(audio_files, card_durations):
                with wave.open(str(audio_path), "rb") as audio:
                    if audio.getparams()[:3] != params[:3]:
                        raise RuntimeError("TTS returned inconsistent audio formats between narration beats.")
                    combined.writeframes(audio.readframes(audio.getnframes()))
                silence_frames = max(0, round((card_duration - _audio_duration(audio_path)) * params.framerate))
                combined.writeframes(b"\0" * silence_frames * params.nchannels * params.sampwidth)

    listing = work / "clips.txt"
    listing.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in video_files) + "\n", encoding="utf-8")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    music = _music_track()
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(joined_audio)]
    if music:
        command += ["-stream_loop", "-1", "-i", str(music)]
        audio_filter = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voice];[2:a]loudnorm=I=-32:TP=-8:LRA=7[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    else:
        audio_filter = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    command += [
        "-filter_complex", audio_filter, "-map", "0:v:0", "-map", "[aout]", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-ar", "48000", "-b:a", "160k", "-t", f"{total_duration:.3f}", "-shortest",
        "-movflags", "+faststart", str(output_path),
    ]
    subprocess.run(command, check=True)
    probe = json.loads(subprocess.check_output([
        shutil.which("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output_path)
    ], text=True))
    video_stream = next((stream for stream in probe["streams"] if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in probe["streams"] if stream.get("codec_type") == "audio"), None)
    actual_duration = float(probe.get("format", {}).get("duration", 0))
    if not video_stream or (video_stream.get("codec_name"), video_stream.get("width"), video_stream.get("height"), video_stream.get("r_frame_rate")) != ("h264", WIDTH, HEIGHT, f"{FPS}/1"):
        raise RuntimeError("Rendered video failed the H.264 1080x1920 30 FPS validation.")
    if not audio_stream or audio_stream.get("codec_name") != "aac":
        raise RuntimeError("Rendered video failed the AAC audio validation.")
    if not MIN_DURATION <= actual_duration <= MAX_DURATION:
        raise RuntimeError(f"Narrated video duration is {actual_duration:.1f}s; expected 15-20s.")
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
