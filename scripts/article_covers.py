"""Generate original branded 1200x630 social cards for Macca Blog articles."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "blog" / "posts.json"
OUT_DIR = ROOT / "blog" / "assets" / "covers"
BACKGROUND_CANDIDATES = (
    ROOT / "images" / "macca-blog-banner.jpg",
    ROOT / "images" / "macca-blog-banner.webp",
)


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


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int, max_lines: int = 4):
    words = re.sub(r"\s+", " ", text).strip().split()
    lines, current = [], ""
    for word in words:
        next_line = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), next_line, font=fnt)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,:;-") + "…"
    return lines


def background():
    for candidate in BACKGROUND_CANDIDATES:
        if candidate.is_file():
            with Image.open(candidate) as image:
                return image.convert("RGB")
    return Image.new("RGB", (1200, 630), "#100d1b")


def render(post: dict, output: Path):
    base = ImageOps.fit(background(), (1200, 630), method=Image.Resampling.LANCZOS).convert("RGBA")
    base = Image.alpha_composite(base, Image.new("RGBA", base.size, (6, 5, 16, 118)))
    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle((54, 248, 1146, 566), radius=34, fill=(13, 9, 28, 224), outline=(255, 104, 173, 195), width=3)
    draw.rounded_rectangle((58, 72, 290, 112), radius=20, fill=(77, 224, 237, 245))
    draw.text((78, 79), "MACCA BLOG", font=font(24, True), fill=(8, 7, 18, 255))
    category = str(post.get("category") or "GTA & ROCKSTAR").upper()[:40]
    draw.text((58, 154), category, font=font(24, True), fill=(77, 224, 237, 255))

    title = str(post.get("title") or "GTA & Rockstar News")
    size = 56
    while size >= 34:
        fnt = font(size, True)
        lines = wrap(draw, title, fnt, 980, 4)
        if len(lines) * int(size * 1.2) <= 245:
            break
        size -= 2
    y = 290
    for line in lines:
        draw.text((86, y), line, font=fnt, fill=(255, 247, 242, 255), stroke_width=1, stroke_fill=(8, 5, 17, 220))
        y += int(size * 1.2)

    draw.text((84, 530), "macca-lab.onrender.com/blog", font=font(22, False), fill=(227, 211, 231, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output, "JPEG", quality=91, optimize=True)


def main():
    posts = json.loads(POSTS.read_text(encoding="utf-8"))
    changed = False
    for post in posts:
        slug = str(post.get("slug") or "").strip()
        if not slug:
            continue
        output = OUT_DIR / f"{slug}.jpg"
        # Regenerate when missing. New article titles get a new slug, so existing
        # cards remain stable and old builds stay cheap.
        if not output.is_file():
            render(post, output)
            print(f"Generated {output.relative_to(ROOT)}")
        desired = f"/blog/assets/covers/{slug}.jpg"
        if post.get("socialImage") != desired:
            post["socialImage"] = desired
            changed = True
    if changed:
        POSTS.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
