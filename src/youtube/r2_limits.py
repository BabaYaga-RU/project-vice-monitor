"""Hard, never-auto-increased R2 upload limits with persistent reservations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

MAX_OBJECT_BYTES = 25 * 1024 * 1024
MAX_UPLOAD_ATTEMPTS_24H = 24
MAX_UPLOAD_ATTEMPTS_MONTH = 750
MAX_ATTEMPTS_PER_OBJECT = 2
MAX_OBJECTS_PER_RUN = 1


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (AttributeError, ValueError):
        return None


def reserve_r2_upload(
    state: dict,
    *,
    slug: str,
    object_key: str,
    size_bytes: int,
    now: datetime | None = None,
    objects_reserved_this_run: int = 0,
) -> tuple[int, str]:
    """Reserve bounded PUT attempts before network I/O; returns (count, reason).

    Reservations count against the quotas even when a subsequent request fails
    or the runner is interrupted. This intentionally errs on the safe side.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    if size_bytes < 0 or size_bytes > MAX_OBJECT_BYTES:
        return 0, "MP4 exceeds the 25 MB R2 limit."
    if objects_reserved_this_run >= MAX_OBJECTS_PER_RUN:
        return 0, "Per-run R2 object limit reached."
    articles = state.setdefault("articles", {})
    if slug in articles:
        return 0, "This article already has an R2 object reservation."

    month = now.strftime("%Y-%m")
    if state.get("month") != month:
        state["month"] = month
        state["monthlyUploadAttempts"] = 0
    state.setdefault("monthlyUploadAttempts", 0)

    cutoff = now - timedelta(hours=24)
    recent = []
    for value in state.get("recentUploadAttempts24h", []):
        parsed = _parse_timestamp(value)
        if parsed and cutoff < parsed <= now:
            recent.append(parsed.isoformat().replace("+00:00", "Z"))
    state["recentUploadAttempts24h"] = recent

    daily_remaining = MAX_UPLOAD_ATTEMPTS_24H - len(recent)
    monthly_remaining = MAX_UPLOAD_ATTEMPTS_MONTH - int(state["monthlyUploadAttempts"])
    attempts = min(MAX_ATTEMPTS_PER_OBJECT, daily_remaining, monthly_remaining)
    if attempts <= 0:
        return 0, "R2 daily or monthly upload-attempt limit reached."

    timestamp = now.isoformat().replace("+00:00", "Z")
    # Reserve every allowed try before sending any bytes. Unused reservations
    # remain charged to the local ledger, preventing workflow replays from
    # exceeding the fixed operation cap.
    state["recentUploadAttempts24h"].extend([timestamp] * attempts)
    state["monthlyUploadAttempts"] += attempts
    articles[slug] = {
        "objectKey": object_key,
        "month": month,
        "attemptsReserved": attempts,
        "reservedAt": timestamp,
        "sizeBytes": size_bytes,
    }
    return attempts, ""
