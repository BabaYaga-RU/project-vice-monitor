"""Render one shared local video per queued article and stage Reels on optional R2."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

import boto3

from src.youtube.shorts import create_short

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = Path(os.environ.get("SOCIAL_VIDEO_DIR", Path(os.environ.get("RUNNER_TEMP", ".")) / "macca-social-videos"))
MANIFEST = Path(os.environ.get("INSTAGRAM_REEL_MANIFEST_FILE", Path(os.environ.get("RUNNER_TEMP", ".")) / "macca-reel-manifest.json"))


def _read(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def main() -> None:
    ig_queue = _read(Path(os.environ.get("INSTAGRAM_QUEUE_FILE", ROOT / "blog" / "instagram-queue.json")), [])
    yt_queue = _read(Path(os.environ.get("YOUTUBE_QUEUE_FILE", ROOT / "blog" / "youtube-queue.json")), [])
    posts = _read(ROOT / "blog" / "posts.json", [])
    slugs = list(dict.fromkeys(item.get("slug") for item in [*ig_queue, *yt_queue] if item.get("slug")))
    by_slug = {item.get("slug"): item for item in posts}
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"schemaVersion": 1, "videos": {}}
    r2_names = (
        "CLOUDFLARE_R2_ACCOUNT_ID", "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY", "CLOUDFLARE_R2_BUCKET",
        "CLOUDFLARE_R2_PUBLIC_BASE_URL",
    )
    r2_ready = all(os.environ.get(name) for name in r2_names)
    s3 = None
    public_base = os.environ.get("CLOUDFLARE_R2_PUBLIC_BASE_URL", "").rstrip("/")
    if r2_ready:
        account = os.environ["CLOUDFLARE_R2_ACCOUNT_ID"]
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )

    for slug in slugs:
        article = by_slug.get(slug)
        if not article:
            print(f"Queued social video skipped; article not found: {slug}")
            continue
        output = VIDEO_DIR / f"{slug}.mp4"
        if not output.is_file():
            with __import__("tempfile").TemporaryDirectory(prefix="macca-render-") as work:
                create_short(article, output, work)
        entry = {"localPath": str(output)}
        if s3 and os.environ.get("SHORTS_RENDERER", "narrated").lower() != "legacy" and any(item.get("slug") == slug for item in ig_queue):
            object_key = f"instagram-reels/{uuid.uuid4().hex}-{slug}.mp4"
            s3.upload_file(str(output), os.environ["CLOUDFLARE_R2_BUCKET"], object_key, ExtraArgs={"ContentType": "video/mp4", "CacheControl": "public, max-age=3600"})
            url = f"{public_base}/{object_key}"
            # Confirm public reachability before asking Meta to fetch the object.
            request = Request(url, method="HEAD", headers={"User-Agent": "MaccaSocialPublisher/1.0"})
            try:
                with urlopen(request, timeout=20) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Temporary Reel URL returned HTTP {response.status}.")
            except Exception:
                s3.delete_object(Bucket=os.environ["CLOUDFLARE_R2_BUCKET"], Key=object_key)
                raise
            entry.update({"reelUrl": url, "r2ObjectKey": object_key})
        manifest["videos"][slug] = entry
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Prepared shared vertical video for {slug} ({output.stat().st_size} bytes).")
    if not slugs:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not r2_ready:
        print("R2 Reel staging is not configured; Instagram will use its existing square-image fallback.")


def cleanup() -> None:
    data = _read(MANIFEST, {"videos": {}})
    names = ("CLOUDFLARE_R2_ACCOUNT_ID", "CLOUDFLARE_R2_ACCESS_KEY_ID", "CLOUDFLARE_R2_SECRET_ACCESS_KEY", "CLOUDFLARE_R2_BUCKET")
    if all(os.environ.get(name) for name in names):
        account = os.environ["CLOUDFLARE_R2_ACCOUNT_ID"]
        s3 = boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com", aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"], region_name="auto")
        for entry in data.get("videos", {}).values():
            key = entry.get("r2ObjectKey")
            if key:
                s3.delete_object(Bucket=os.environ["CLOUDFLARE_R2_BUCKET"], Key=key)
                print("Deleted temporary Reel video from R2.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup()
    else:
        main()
