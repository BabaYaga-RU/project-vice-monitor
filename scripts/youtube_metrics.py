"""Collect optional YouTube Analytics snapshots without changing topic ranking.

The Analytics API reports these content metrics by calendar date, not as exact
rolling 6/24/72-hour intervals. We store that limitation alongside each sample.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.discovery import build

from src.youtube.analytics_auth import analytics_credentials_from_environment
from src.youtube.auth import YouTubeAuthenticationError

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = Path(os.environ.get("YOUTUBE_PUBLISHED_FILE", ROOT / "blog" / "youtube-published.json"))
METRICS = Path(os.environ.get("YOUTUBE_METRICS_FILE", ROOT / "blog" / "youtube-metrics.json"))
MILESTONES = (6, 24, 72)
METRIC_NAMES = (
    "views", "engagedViews", "averageViewDuration", "averageViewPercentage",
    "likes", "comments", "shares", "subscribersGained",
)


def _read(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect() -> int:
    published = _read(PUBLISHED, [])
    store = _read(METRICS, {"schemaVersion": 1, "videos": {}})
    videos = store.setdefault("videos", {})
    now = datetime.now(timezone.utc)
    service = build("youtubeAnalytics", "v2", credentials=analytics_credentials_from_environment(), cache_discovery=False)
    collected = 0
    for record in published:
        video_id = record.get("youtubeVideoId")
        if not video_id:
            continue
        try:
            published_at = datetime.fromisoformat(record["publishedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        entry = videos.setdefault(video_id, {
            "slug": record.get("slug", ""), "articleUrl": record.get("articleUrl", ""),
            "youtubeUrl": record.get("youtubeUrl", f"https://www.youtube.com/watch?v={video_id}"),
            "publishedAt": published_at.isoformat(), "snapshots": [],
        })
        completed = {snapshot.get("targetHours") for snapshot in entry.get("snapshots", [])}
        age_hours = (now - published_at).total_seconds() / 3600
        for target in MILESTONES:
            if target in completed or age_hours < target:
                continue
            # Keep one sample for each milestone; reports aggregate UTC dates,
            # so this is explicitly calendar-day-to-date, not rolling-hour data.
            start_date = published_at.date().isoformat()
            end_date = now.date().isoformat()
            response = service.reports().query(
                ids="channel==MINE", startDate=start_date, endDate=end_date,
                filters=f"video=={video_id}", metrics=",".join(METRIC_NAMES),
            ).execute()
            rows = response.get("rows") or []
            if not rows:
                print(f"Analytics for {video_id} not available yet; it will be retried.")
                continue
            values = dict(zip([header["name"] for header in response["columnHeaders"]], rows[0]))
            entry.setdefault("snapshots", []).append({
                "targetHours": target,
                "actualAgeHours": round(age_hours, 1),
                "collectedAt": now.isoformat(),
                "dataPeriod": {"startDate": start_date, "endDate": end_date, "basis": "UTC calendar days; not an exact rolling-hour window"},
                "metrics": {name: values.get(name) for name in METRIC_NAMES},
            })
            collected += 1
    _write(METRICS, store)
    print(f"Saved {collected} YouTube Analytics snapshot(s). Topic ranking remains unchanged.")
    return collected


if __name__ == "__main__":
    try:
        collect()
    except YouTubeAuthenticationError as error:
        print(str(error))
        raise SystemExit(1)
