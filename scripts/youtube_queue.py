"""Create, render, upload, and persist Macca Blog YouTube Shorts."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from src.youtube.auth import YouTubeAuthenticationError
from src.youtube.shorts import create_short
from src.youtube.upload import upload_video

ROOT = Path(__file__).resolve().parents[1]
QUEUE = Path(os.environ.get("YOUTUBE_QUEUE_FILE", ROOT / "blog" / "youtube-queue.json"))
PUBLISHED = Path(os.environ.get("YOUTUBE_PUBLISHED_FILE", ROOT / "blog" / "youtube-published.json"))
SOCIAL_VIDEO_DIR = Path(os.environ.get("SOCIAL_VIDEO_DIR", Path(os.environ.get("RUNNER_TEMP", ".")) / "macca-social-videos"))


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def youtube_description(item: dict) -> str:
    blocks = [str(item.get("description", "")).strip()[:900]]
    for section in item.get("sections", []):
        if len(blocks) >= 4:
            break
        heading = str(section.get("heading", "")).strip()
        paragraphs = [str(value).strip() for value in section.get("paragraphs", []) if str(value).strip()]
        if heading and paragraphs:
            blocks.append(f"{heading}\n" + "\n\n".join(paragraphs)[:750])
    blocks.append(f"Read the full story: {item.get('articleUrl', '')}")
    sources = item.get("sources", [])
    references = [f"- {source.get('title', 'Source')}: {source.get('url', '')}" for source in sources[:5] if source.get("url")]
    if references:
        blocks.append("Sources\n" + "\n".join(references)[:1300])
    blocks.append("Subscribe to Macca the Gator: https://www.youtube.com/@macca_the_gator_oficial")

    hashtags = ["#GTA", "#GrandTheftAuto", "#RockstarGames", "#MaccaTheGator", "#Shorts"]
    for tag in item.get("tags", []):
        compact = "".join(ch for ch in str(tag).title() if ch.isalnum())
        if compact:
            hashtags.append("#" + compact)
    hashtag_text = " ".join(dict.fromkeys(hashtags))
    body = "\n\n".join(block for block in blocks if block)
    return body[:5000 - len(hashtag_text) - 2] + "\n\n" + hashtag_text


def publish_pending() -> int:
    queue = read_json(QUEUE, [])
    published = read_json(PUBLISHED, [])
    published_slugs = {item.get("slug") for item in published}
    remaining = []
    success_count = 0
    for queue_index, item in enumerate(queue):
        slug = item.get("slug")
        if not slug or slug in published_slugs:
            continue
        title = f"{item.get('title', 'GTA & Rockstar News')} | Macca the Gator"[:100]
        description = youtube_description(item)
        try:
            cached_video = SOCIAL_VIDEO_DIR / f"{slug}.mp4"
            upload_options = {
                "title": title,
                "description": description,
                "tags": list(dict.fromkeys(["GTA", "Grand Theft Auto", "Rockstar Games", "Macca the Gator", "Shorts", *item.get("tags", [])]))[:500],
                "privacy_status": "public",
            }
            if cached_video.is_file():
                result = upload_video(cached_video, **upload_options)
            else:
                with tempfile.TemporaryDirectory(prefix="macca-youtube-") as temp:
                    path = create_short(item, Path(temp) / "macca-short.mp4", temp)
                    result = upload_video(path, **upload_options)
            record = {
                "slug": slug,
                "articleUrl": item.get("articleUrl", ""),
                "youtubeVideoId": result["id"],
                "youtubeUrl": result["url"],
                "publishedAt": datetime.now(timezone.utc).isoformat(),
            }
            published.append(record)
            published_slugs.add(slug)
            success_count += 1
            print(f"Public YouTube Short uploaded for {slug}: {result['url']}")
        except YouTubeAuthenticationError as exc:
            remaining.append(item)
            retained_slugs = {entry.get("slug") for entry in remaining}
            remaining.extend(
                entry for entry in queue[queue_index + 1:]
                if entry.get("slug") not in published_slugs and entry.get("slug") not in retained_slugs
            )
            print(str(exc))
            print("YouTube queue retained for retry; authentication failure stopped this run.")
            break
        except Exception:
            remaining.append(item)
            print(f"YouTube upload failed for {slug}; item retained for retry.")
    if remaining:
        write_json(QUEUE, remaining)
    else:
        QUEUE.unlink(missing_ok=True)
    if success_count:
        write_json(PUBLISHED, published)
    print(f"YouTube queue result: {success_count} uploaded; {len(remaining)} retained for retry.")
    return success_count


if __name__ == "__main__":
    publish_pending()
