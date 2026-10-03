"""Publish a weekly horizontal GTA/Rockstar recap using existing blog posts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.youtube.kokoro_tts import LocalNarrator
from src.youtube.upload import set_thumbnail, upload_video

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "blog" / "posts.json"
STATE = ROOT / "blog" / "youtube-weekly.json"
WIDTH, HEIGHT, FPS = 1920, 1080, 30


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def wrap(draw, text: str, fnt, max_width: int, max_lines: int):
    words = re.sub(r"\s+", " ", text).strip().split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=fnt)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,:;-") + "…"
    return lines


def background():
    for candidate in (ROOT / "images" / "macca-blog-banner.jpg", ROOT / "images" / "macca-blog-banner.webp"):
        if candidate.is_file():
            with Image.open(candidate) as image:
                return image.convert("RGB")
    return Image.new("RGB", (WIDTH, HEIGHT), "#100d1b")


def render_card(path: Path, heading: str, body: str, index: int, total: int):
    image = ImageOps.fit(background(), (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS).convert("RGBA")
    image = Image.alpha_composite(image, Image.new("RGBA", image.size, (7, 5, 17, 126)))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((88, 160, 1832, 914), radius=50, fill=(14, 9, 28, 224), outline=(255, 104, 173, 200), width=4)
    draw.text((120, 76), "MACCA THE GATOR  |  WEEKLY GTA & ROCKSTAR RECAP", font=font(34, True), fill=(77, 224, 237, 255))
    draw.text((120, 210), f"{index:02d} / {total:02d}", font=font(28, True), fill=(255, 154, 107, 255))
    title_font = font(58, True)
    y = 300
    for line in wrap(draw, heading, title_font, 1530, 3):
        draw.text((145, y), line, font=title_font, fill=(255, 247, 242, 255))
        y += 76
    body_font = font(34, False)
    y += 34
    for line in wrap(draw, body, body_font, 1530, 5):
        draw.text((145, y), line, font=body_font, fill=(229, 215, 233, 255))
        y += 48
    draw.text((145, 850), "Full sources and stories: macca-lab.onrender.com/blog", font=font(27, True), fill=(77, 224, 237, 255))
    image.convert("RGB").save(path, "JPEG", quality=92)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def latest_posts():
    posts = read_json(POSTS, [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).date()
    candidates = []
    for post in posts:
        try:
            date = datetime.fromisoformat(str(post.get("date"))).date()
        except ValueError:
            continue
        if date >= cutoff:
            candidates.append(post)
    # Prefer concrete GTA 6/Rockstar developments and featured stories, but
    # never invent a ranking outside the material already published.
    def score(post):
        text = f"{post.get('title','')} {post.get('description','')}".lower()
        value = 3 if re.search(r"gta\s*6|gta\s*vi|rockstar", text) else 0
        value += 1 if post.get("featured") else 0
        value += 1 if re.search(r"confirm|release|map|weather|trailer|price|collector|online", text) else 0
        return value
    candidates.sort(key=lambda post: (score(post), str(post.get("date", ""))), reverse=True)
    return candidates[:5]


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required.")
    posts = latest_posts()
    if len(posts) < 3:
        print("Fewer than three recent stories; weekly recap skipped.")
        return

    now = datetime.now(timezone.utc)
    week_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    state = read_json(STATE, {"published": []})
    if any(item.get("week") == week_key for item in state.get("published", [])):
        print(f"Weekly recap {week_key} already published.")
        return

    title = "This Week in GTA 6 & Rockstar: 5 Stories You Missed"
    intro = "Here are the biggest GTA and Rockstar stories Macca Blog covered this week."
    beats = [(title, intro)]
    for post in posts:
        hook = str(post.get("socialHook") or post.get("description") or post.get("title") or "").strip()
        beats.append((str(post.get("youtubeTitle") or post.get("title") or "GTA story"), hook[:360]))
    beats.append(("Read every story on Macca Blog", "The full stories and source links are available on Macca Blog. Use the links in this video's description."))

    with tempfile.TemporaryDirectory(prefix="macca-weekly-") as temp:
        work = Path(temp)
        narrator = LocalNarrator(work / "tts-metadata.json")
        audio_paths = [work / f"voice-{i:02d}.wav" for i in range(len(beats))]
        narrator.synthesize([narration for _, narration in beats], audio_paths, 1.0)
        clips = []
        for index, ((heading, body), audio) in enumerate(zip(beats, audio_paths), 1):
            card = work / f"card-{index:02d}.jpg"
            render_card(card, heading, body, index, len(beats))
            duration = max(4.2, wav_duration(audio) + 0.35)
            clip = work / f"clip-{index:02d}.mp4"
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-loop", "1", "-i", str(card), "-i", str(audio),
                "-t", f"{duration:.3f}", "-vf", f"fps={FPS},format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-c:a", "aac", "-ac", "2", "-ar", "48000", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(clip),
            ], check=True)
            clips.append(clip)

        listing = work / "clips.txt"
        listing.write_text("\n".join(f"file '{clip.as_posix()}'" for clip in clips) + "\n", encoding="utf-8")
        output = work / "weekly.mp4"
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart", str(output),
        ], check=True)

        links = "\n".join(
            f"{index}. {post.get('title','Story')}\nhttps://macca-lab.onrender.com/blog/{post.get('slug','')}/"
            for index, post in enumerate(posts, 1)
        )
        description = (
            "Five GTA and Rockstar stories from the last week, sourced on Macca Blog.\n\n"
            + links
            + "\n\n#GTA6 #RockstarGames #GrandTheftAuto"
        )
        result = upload_video(
            output,
            title=title,
            description=description,
            tags=["GTA 6", "GTA VI", "Grand Theft Auto 6", "Rockstar Games", "GTA News", "Macca the Gator"],
            privacy_status="public",
        )

        thumb_article = {"title": title, "youtubeTitle": title, "socialHook": title}
        from src.youtube.shorts import create_thumbnail
        thumbnail = create_thumbnail(thumb_article, work / "weekly-thumbnail.jpg", work / "thumb")
        try:
            set_thumbnail(result["id"], thumbnail)
        except Exception as exc:
            print(f"Weekly thumbnail update skipped: {exc}")

    state.setdefault("published", []).append({
        "week": week_key,
        "youtubeVideoId": result["id"],
        "youtubeUrl": result["url"],
        "publishedAt": datetime.now(timezone.utc).isoformat(),
        "stories": [post.get("slug", "") for post in posts],
    })
    write_json(STATE, state)
    print(f"Published weekly recap: {result['url']}")


if __name__ == "__main__":
    main()
