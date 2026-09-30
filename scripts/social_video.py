"""Render one shared local video per queued article and stage Reels on optional R2."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config

from src.youtube.shorts import create_short
from src.youtube.r2_limits import MAX_OBJECTS_PER_RUN, MAX_ATTEMPTS_PER_OBJECT, MAX_OBJECT_BYTES, reserve_r2_upload

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = Path(os.environ.get("SOCIAL_VIDEO_DIR", Path(os.environ.get("RUNNER_TEMP", ".")) / "macca-social-videos"))
MANIFEST = Path(os.environ.get("INSTAGRAM_REEL_MANIFEST_FILE", Path(os.environ.get("RUNNER_TEMP", ".")) / "macca-reel-manifest.json"))
USAGE_FILE = Path(os.environ.get("R2_USAGE_FILE", ROOT / "blog" / "r2-upload-usage.json"))


def _read(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _r2_configured() -> bool:
    names = (
        "CLOUDFLARE_R2_ACCOUNT_ID", "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY", "CLOUDFLARE_R2_BUCKET",
        "CLOUDFLARE_R2_PUBLIC_BASE_URL",
    )
    return all(os.environ.get(name) for name in names)


def _r2_client():
    account = os.environ["CLOUDFLARE_R2_ACCOUNT_ID"]
    return boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        # Disable botocore's hidden retries; explicit retry loops below are capped.
        config=Config(retries={"total_max_attempts": 1, "mode": "standard"}),
    )


def main() -> None:
    ig_queue = _read(Path(os.environ.get("INSTAGRAM_QUEUE_FILE", ROOT / "blog" / "instagram-queue.json")), [])
    yt_queue = _read(Path(os.environ.get("YOUTUBE_QUEUE_FILE", ROOT / "blog" / "youtube-queue.json")), [])
    posts = _read(ROOT / "blog" / "posts.json", [])
    slugs = list(dict.fromkeys(item.get("slug") for item in [*ig_queue, *yt_queue] if item.get("slug")))
    by_slug = {item.get("slug"): item for item in posts}
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"schemaVersion": 1, "videos": {}}
    r2_ready = _r2_configured()
    usage = _read(USAGE_FILE, {"schemaVersion": 1, "month": "", "monthlyUploadAttempts": 0, "recentUploadAttempts24h": [], "articles": {}})
    objects_reserved_this_run = 0

    for slug in slugs:
        article = by_slug.get(slug)
        if not article:
            print(f"Queued social video skipped; article not found: {slug}")
            continue
        output = VIDEO_DIR / f"{slug}.mp4"
        if not output.is_file():
            with tempfile.TemporaryDirectory(prefix="macca-render-") as work:
                create_short(article, output, work)
        entry = {"localPath": str(output)}
        queued_for_instagram = any(item.get("slug") == slug for item in ig_queue)
        if r2_ready and os.environ.get("SHORTS_RENDERER", "narrated").lower() != "legacy" and queued_for_instagram:
            object_key = f"instagram-reels/{uuid.uuid4().hex}-{slug}.mp4"
            attempts, reason = reserve_r2_upload(
                usage, slug=slug, object_key=object_key, size_bytes=output.stat().st_size,
                objects_reserved_this_run=objects_reserved_this_run,
            )
            if attempts:
                objects_reserved_this_run += 1
                _write(USAGE_FILE, usage)
                entry.update({"r2ObjectKey": object_key, "attemptsReserved": attempts, "uploadStarted": False})
                print(f"Reserved {attempts} bounded R2 attempt(s) for {slug}; quota is persisted before network upload.")
            else:
                print(f"R2 blocked for {slug}: {reason} Instagram will use the square-image fallback.")
        manifest["videos"][slug] = entry
        _write(MANIFEST, manifest)
        print(f"Prepared shared vertical video for {slug} ({output.stat().st_size} bytes).")
    if not slugs:
        _write(MANIFEST, manifest)
    if not r2_ready:
        print("R2 Reel staging is not configured; Instagram will use its existing square-image fallback.")


def upload_reel_objects() -> None:
    manifest = _read(MANIFEST, {"videos": {}})
    if not _r2_configured():
        print("R2 is not configured; no video was sent. Instagram will use the image fallback.")
        return
    items = list(manifest.get("videos", {}).items())
    s3 = None
    uploaded_objects_this_run = 0
    for slug, entry in items:
        key = entry.get("r2ObjectKey")
        attempts = min(MAX_ATTEMPTS_PER_OBJECT, int(entry.get("attemptsReserved", 0)))
        if not key or attempts <= 0:
            continue
        if uploaded_objects_this_run >= MAX_OBJECTS_PER_RUN:
            print("R2 per-run guard stopped unexpected additional object uploads.")
            break
        uploaded_objects_this_run += 1
        path = Path(entry.get("localPath", ""))
        try:
            size = path.stat().st_size
        except OSError:
            print(f"R2 blocked for {slug}: local MP4 is missing; Instagram will use the image fallback.")
            continue
        if size > MAX_OBJECT_BYTES:
            print(f"R2 blocked for {slug}: MP4 exceeds 25 MB; Instagram will use the image fallback.")
            continue
        if s3 is None:
            try:
                s3 = _r2_client()
            except Exception as error:
                print(f"R2 unavailable ({type(error).__name__}); Instagram will use the image fallback.")
                return
        entry["uploadStarted"] = True
        _write(MANIFEST, manifest)
        payload = path.read_bytes()
        success = False
        for attempt in range(1, attempts + 1):
            try:
                s3.put_object(
                    Bucket=os.environ["CLOUDFLARE_R2_BUCKET"], Key=key,
                    Body=payload, ContentLength=len(payload), ContentType="video/mp4",
                    CacheControl="public, max-age=3600",
                )
                entry["uploaded"] = True
                success = True
                print(f"R2 object uploaded for {slug} (attempt {attempt}/{attempts}).")
                break
            except Exception as error:
                print(f"R2 upload attempt {attempt}/{attempts} failed ({type(error).__name__}); no unbounded retry.")
        if success:
            public_base = os.environ["CLOUDFLARE_R2_PUBLIC_BASE_URL"].rstrip("/")
            url = f"{public_base}/{key}"
            request = Request(url, method="HEAD", headers={"User-Agent": "MaccaSocialPublisher/1.0"})
            try:
                with urlopen(request, timeout=20) as response:
                    if response.status == 200 and response.headers.get("content-type", "").startswith("video/mp4"):
                        entry["reelUrl"] = url
                        print(f"R2 public URL verified: {url} (HTTP 200, video/mp4).")
                    else:
                        print(f"Temporary R2 video is not publicly reachable as video/mp4 (HTTP {response.status}); image fallback selected.")
            except Exception as error:
                print(f"Temporary R2 video could not be verified ({type(error).__name__}); image fallback selected.")
        if not entry.get("reelUrl"):
            print(f"Reel staging unavailable for {slug}; Instagram will use the square-image fallback.")
        _write(MANIFEST, manifest)


def cleanup() -> None:
    data = _read(MANIFEST, {"videos": {}})
    names = ("CLOUDFLARE_R2_ACCOUNT_ID", "CLOUDFLARE_R2_ACCESS_KEY_ID", "CLOUDFLARE_R2_SECRET_ACCESS_KEY", "CLOUDFLARE_R2_BUCKET")
    if _r2_configured():
        s3 = None
        for entry in data.get("videos", {}).values():
            key = entry.get("r2ObjectKey")
            if not key or not entry.get("uploadStarted"):
                continue
            try:
                if s3 is None:
                    s3 = _r2_client()
                deleted = False
                for attempt in range(1, MAX_ATTEMPTS_PER_OBJECT + 1):
                    try:
                        s3.delete_object(Bucket=os.environ["CLOUDFLARE_R2_BUCKET"], Key=key)
                        deleted = True
                        break
                    except Exception as error:
                        print(f"R2 cleanup attempt {attempt}/{MAX_ATTEMPTS_PER_OBJECT} failed ({type(error).__name__}).")
                if deleted:
                    print("Temporary Instagram Reel object deleted from R2.")
                else:
                    print("R2 deletion did not complete; the configured one-day lifecycle remains the fallback.")
            except Exception as error:
                print(f"R2 cleanup unavailable ({type(error).__name__}); the one-day lifecycle remains the fallback.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup()
    elif len(sys.argv) > 1 and sys.argv[1] == "upload":
        upload_reel_objects()
    else:
        main()
