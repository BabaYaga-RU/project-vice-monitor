"""Collect YouTube Analytics daily performance and audience-retention data.

The API reports channel analytics by calendar date. This collector therefore
stores dated samples instead of pretending they are exact rolling 6/24/72-hour
windows. Retention is collected separately at roughly 24h and 72h because the
API can lag behind publication.
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
METRIC_NAMES = (
    "views", "engagedViews", "averageViewDuration", "averageViewPercentage",
    "likes", "comments", "shares", "subscribersGained",
)
RETENTION_METRICS = ("audienceWatchRatio", "relativeRetentionPerformance")


def _read(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _headers(response):
    return [header["name"] for header in response.get("columnHeaders", [])]


def _quality_flags(metrics: dict) -> list[str]:
    flags = []
    percentage = metrics.get("averageViewPercentage")
    duration = metrics.get("averageViewDuration")
    try:
        percentage = float(percentage)
    except (TypeError, ValueError):
        percentage = None
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = None
    if percentage is not None and percentage > 150:
        flags.append("heavy_rewatch_or_reporting_outlier")
    if percentage is not None and percentage > 300:
        flags.append("exclude_from_automatic_learning")
    if duration is not None and duration < 0:
        flags.append("invalid_duration")
    return flags


def _aggregate_sample(service, video_id: str, start_date: str, end_date: str):
    response = service.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        filters=f"video=={video_id}",
        metrics=",".join(METRIC_NAMES),
    ).execute()
    rows = response.get("rows") or []
    if not rows:
        return None
    values = dict(zip(_headers(response), rows[0]))
    metrics = {name: values.get(name) for name in METRIC_NAMES}
    return {"metrics": metrics, "qualityFlags": _quality_flags(metrics)}


def _daily_rows(service, video_id: str, start_date: str, end_date: str) -> list[dict]:
    response = service.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        dimensions="day",
        filters=f"video=={video_id}",
        metrics=",".join(METRIC_NAMES),
        sort="day",
    ).execute()
    headers = _headers(response)
    rows = []
    for raw in response.get("rows") or []:
        values = dict(zip(headers, raw))
        day = values.pop("day", None)
        if not day:
            continue
        metrics = {name: values.get(name) for name in METRIC_NAMES}
        rows.append({"date": day, "metrics": metrics, "qualityFlags": _quality_flags(metrics)})
    return rows


def _retention(service, video_id: str, start_date: str, end_date: str) -> list[dict]:
    response = service.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        dimensions="elapsedVideoTimeRatio",
        filters=f"video=={video_id}",
        metrics=",".join(RETENTION_METRICS),
        sort="elapsedVideoTimeRatio",
    ).execute()
    headers = _headers(response)
    points = []
    for raw in response.get("rows") or []:
        values = dict(zip(headers, raw))
        ratio = values.get("elapsedVideoTimeRatio")
        if ratio is None:
            continue
        points.append({
            "elapsedVideoTimeRatio": ratio,
            "audienceWatchRatio": values.get("audienceWatchRatio"),
            "relativeRetentionPerformance": values.get("relativeRetentionPerformance"),
        })
    return points


def collect() -> int:
    published = _read(PUBLISHED, [])
    store = _read(METRICS, {"schemaVersion": 2, "videos": {}})
    store["schemaVersion"] = 2
    videos = store.setdefault("videos", {})
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    service = build(
        "youtubeAnalytics", "v2",
        credentials=analytics_credentials_from_environment(),
        cache_discovery=False,
    )
    changes = 0

    for record in published:
        video_id = record.get("youtubeVideoId")
        if not video_id:
            continue
        try:
            published_at = datetime.fromisoformat(record["publishedAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue

        age_hours = max(0.0, (now - published_at).total_seconds() / 3600)
        start_date = published_at.date().isoformat()
        entry = videos.setdefault(video_id, {})
        entry.update({
            "slug": record.get("slug", entry.get("slug", "")),
            "articleUrl": record.get("articleUrl", entry.get("articleUrl", "")),
            "youtubeUrl": record.get("youtubeUrl", entry.get("youtubeUrl", f"https://www.youtube.com/watch?v={video_id}")),
            "publishedAt": published_at.isoformat(),
        })

        samples = entry.setdefault("samples", [])
        if not any(sample.get("collectedDate") == today for sample in samples):
            try:
                sample = _aggregate_sample(service, video_id, start_date, today)
                if sample:
                    samples.append({
                        "collectedDate": today,
                        "collectedAt": now.isoformat(),
                        "actualAgeHours": round(age_hours, 1),
                        "dataPeriod": {
                            "startDate": start_date,
                            "endDate": today,
                            "basis": "UTC calendar-day cumulative report",
                        },
                        **sample,
                    })
                    changes += 1
                else:
                    print(f"Analytics for {video_id} not available yet; it will be retried.")
            except Exception as exc:
                print(f"Could not collect aggregate analytics for {video_id}: {type(exc).__name__}")

        daily = entry.setdefault("daily", [])
        known_days = {row.get("date") for row in daily}
        try:
            for row in _daily_rows(service, video_id, start_date, today):
                if row["date"] not in known_days:
                    daily.append(row)
                    known_days.add(row["date"])
                    changes += 1
        except Exception as exc:
            print(f"Could not collect daily analytics for {video_id}: {type(exc).__name__}")

        # Retention is expensive and can lag. Capture once after ~24h and once
        # after ~72h, using the exact 100-point retention report when available.
        retention_snapshots = entry.setdefault("retentionSnapshots", [])
        completed_stages = {snap.get("stageHours") for snap in retention_snapshots}
        due_stage = 72 if age_hours >= 72 and 72 not in completed_stages else 24 if age_hours >= 24 and 24 not in completed_stages else None
        if due_stage is not None:
            try:
                points = _retention(service, video_id, start_date, today)
                if points:
                    retention_snapshots.append({
                        "stageHours": due_stage,
                        "actualAgeHours": round(age_hours, 1),
                        "collectedAt": now.isoformat(),
                        "dataPeriod": {
                            "startDate": start_date,
                            "endDate": today,
                            "basis": "UTC calendar days",
                        },
                        "points": points,
                    })
                    changes += 1
                else:
                    print(f"Retention for {video_id} not available yet; it will be retried.")
            except Exception as exc:
                print(f"Could not collect retention for {video_id}: {type(exc).__name__}")

    _write(METRICS, store)
    print(f"Saved {changes} YouTube Analytics update(s). Daily and retention data are ready for future performance learning.")
    return changes


if __name__ == "__main__":
    try:
        collect()
    except YouTubeAuthenticationError as error:
        print(str(error))
        raise SystemExit(1)
