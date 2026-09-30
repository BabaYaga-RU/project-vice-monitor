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


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        description = "\n\n".join(filter(None, [
            item.get("description", ""),
            f"Read the full story: {item.get('articleUrl', '')}",
            f"Source: {item.get('sourceUrl', '')}" if item.get("sourceUrl") else "",
            "#GTA #RockstarGames #MaccaTheGator #Shorts",
        ]))[:5000]
        try:
            with tempfile.TemporaryDirectory(prefix="macca-youtube-") as temp:
                path = create_short(item, Path(temp) / "macca-short.mp4", temp)
                result = upload_video(
                    path,
                    title=title,
                    description=description,
                    tags=["GTA", "Grand Theft Auto", "Rockstar Games", "Macca the Gator", "Shorts"],
                    privacy_status="private",
                )
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
            print(f"Private YouTube Short uploaded for {slug}: {result['url']}")
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
