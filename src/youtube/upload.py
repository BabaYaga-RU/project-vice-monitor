"""Resumable YouTube Data API uploads with bounded retries."""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .auth import credentials_from_environment

RETRIABLE_STATUS_CODES = {500, 502, 503, 504}
MAX_RETRIES = 5


def build_youtube_service():
    """Create a YouTube API client with freshly refreshed credentials."""
    return build(
        "youtube", "v3", credentials=credentials_from_environment(),
        cache_discovery=False,
    )


def authenticated_channel(youtube: Any) -> dict[str, str]:
    """Return the channel ID/title for the account behind the OAuth token."""
    response = youtube.channels().list(part="snippet", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise RuntimeError("The authenticated YouTube account has no accessible channel.")
    channel = items[0]
    return {
        "id": channel["id"],
        "title": channel.get("snippet", {}).get("title", "Unknown channel"),
    }


def upload_video(
    video_path: str | Path,
    *,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy_status: str = "private",
    youtube: Any | None = None,
) -> dict[str, str]:
    """Upload a video resumably and retry transient API/network errors."""
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video file does not exist: {path}")
    if privacy_status not in {"private", "unlisted", "public"}:
        raise ValueError("privacy_status must be private, unlisted, or public")

    youtube = youtube or build_youtube_service()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": (tags or [])[:500],
                "categoryId": "20",
            },
            "status": {"privacyStatus": privacy_status},
        },
        media_body=MediaFileUpload(
            str(path), mimetype="video/*", chunksize=8 * 1024 * 1024, resumable=True
        ),
    )

    response = None
    retries = 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except HttpError as exc:
            if exc.resp.status not in RETRIABLE_STATUS_CODES or retries >= MAX_RETRIES:
                raise RuntimeError(
                    f"YouTube upload failed with HTTP {exc.resp.status}."
                ) from None
            retries += 1
            time.sleep(min(2**retries + random.random(), 60))
        except (OSError, TimeoutError):
            if retries >= MAX_RETRIES:
                raise RuntimeError("YouTube upload failed after repeated network errors.") from None
            retries += 1
            time.sleep(min(2**retries + random.random(), 60))

    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("YouTube upload completed without returning a video ID.")
    return {"id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
