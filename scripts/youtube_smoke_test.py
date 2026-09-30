"""Publish the latest unpublished blog story as a real public Shorts test."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.youtube.auth import YouTubeAuthenticationError
from src.youtube.shorts import create_short
from src.youtube.upload import upload_video
from scripts.youtube_queue import youtube_description

ROOT = Path(__file__).resolve().parents[1]
POSTS_FILE = ROOT / "blog" / "posts.json"
PUBLISHED_FILE = Path(os.environ.get("YOUTUBE_PUBLISHED_FILE", ROOT / "blog" / "youtube-published.json"))
QUEUE_FILE = Path(os.environ.get("YOUTUBE_QUEUE_FILE", ROOT / "blog" / "youtube-queue.json"))


def main() -> None:
    try:
        posts = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
        published = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8")) if PUBLISHED_FILE.exists() else []
        published_slugs = {record.get("slug") for record in published}
        article = next((post for post in posts if post.get("slug") not in published_slugs), None)
        if not article:
            raise RuntimeError("There is no unpublished blog article available for the public test.")
        site_url = os.environ.get("SITE_URL", "https://macca-lab.onrender.com").rstrip("/")
        article_url = f"{site_url}/blog/{article['slug']}/"
        item = {**article, "articleUrl": article_url, "thumbnail": article.get("thumbnail", "")}
        with tempfile.TemporaryDirectory(prefix="macca-youtube-publish-") as temp:
            video = create_short(item, Path(temp) / "macca-short.mp4", temp)
            result = upload_video(
                video,
                title=f"{article.get('title', 'GTA & Rockstar News')} | Macca the Gator"[:100],
                description=youtube_description(item),
                tags=["GTA", "Rockstar Games", "Macca the Gator", "Shorts", *article.get("tags", [])][:500],
                privacy_status="public",
            )
        published.append({"slug": article["slug"], "articleUrl": article_url, "youtubeVideoId": result["id"], "youtubeUrl": result["url"], "publishedAt": datetime.now(timezone.utc).isoformat()})
        PUBLISHED_FILE.write_text(json.dumps(published, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if QUEUE_FILE.exists():
            pending = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            pending = [item for item in pending if item.get("slug") != article["slug"]]
            if pending:
                QUEUE_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                QUEUE_FILE.unlink()
    except YouTubeAuthenticationError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except Exception:
        print("Public YouTube article upload failed; temporary files were removed.")
        raise SystemExit(1) from None
    print(f"Public article Shorts upload completed: {result['url']}")


if __name__ == "__main__":
    main()
