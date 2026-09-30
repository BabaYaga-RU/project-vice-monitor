"""Build deterministic vertical article Shorts using local FFmpeg and Pillow."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


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
            pass
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


def _render_card(path: Path, background: Image.Image, eyebrow: str, text: str, index: int, total: int) -> None:
    image = ImageOps.fit(background.convert("RGB"), (1080, 1920), method=Image.Resampling.LANCZOS)
    tint = Image.new("RGBA", image.size, (12, 8, 24, 112))
    image = Image.alpha_composite(image.convert("RGBA"), tint)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((54, 340, 1026, 1530), radius=48, fill=(14, 10, 27, 205), outline=(255, 104, 173, 210), width=4)
    draw.text((104, 410), "MACCA THE GATOR  |  GTA & ROCKSTAR", font=_font(34, True), fill=(77, 224, 237, 255))
    draw.line((104, 480, 976, 480), fill=(255, 104, 173, 230), width=4)
    draw.text((104, 545), eyebrow.upper()[:48], font=_font(31, True), fill=(255, 154, 107, 255))
    font = _font(56 if len(text) < 180 else 48, True)
    y = 625
    lines = _wrap(draw, text, font, 860)
    if len(lines) > 9:
        lines = lines[:8] + [lines[8][:max(1, len(lines[8]) - 3)] + "..."]
    for line in lines:
        draw.text((104, y), line, font=font, fill=(255, 242, 236, 255), stroke_width=1, stroke_fill=(12, 8, 24, 255))
        y += 76 if font.size > 50 else 66
    draw.text((104, 1430), "READ THE FULL STORY", font=_font(30, True), fill=(77, 224, 237, 255))
    draw.text((104, 1480), f"{index:02d} / {total:02d}   |   MACCA-LAB.ONRENDER.COM/BLOG", font=_font(22, True), fill=(225, 204, 224, 255))
    image.convert("RGB").save(path, quality=92)


def create_short(article: dict, output: str | Path, workdir: str | Path) -> Path:
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    background_path = work / "article-background"
    candidates = [article.get("thumbnail", ""), *[item.get("url", "") for item in article.get("inlineImages", [])]]
    background = None
    for url in candidates:
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MaccaBlogPublisher/1.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(12 * 1024 * 1024)
            background_path.write_bytes(data)
            background = Image.open(background_path).convert("RGB")
            break
        except Exception:
            continue
    if background is None:
        background = Image.open(Path(__file__).resolve().parents[2] / "images" / "macca-blog-banner.jpg").convert("RGB")

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

    listing = work / "slides.txt"
    with listing.open("w", encoding="utf-8") as file:
        for index, (heading, text) in enumerate(slides, 1):
            card = work / f"slide-{index:02d}.jpg"
            _render_card(card, background, heading, text, index, len(slides))
            file.write(f"file '{card.as_posix()}'\n")
            file.write("duration 7\n")
        file.write(f"file '{(work / f'slide-{len(slides):02d}.jpg').as_posix()}'\n")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-vf", "fps=30,scale=1080:1920,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-tune", "stillimage", "-movflags", "+faststart", "-t", str(len(slides) * 7), str(output_path)],
        check=True,
    )
    return output_path


def main() -> None:
    article = json.loads(os.environ["ARTICLE_JSON"])
    create_short(article, os.environ["OUTPUT_VIDEO"], os.environ["WORK_DIR"])


if __name__ == "__main__":
    main()
