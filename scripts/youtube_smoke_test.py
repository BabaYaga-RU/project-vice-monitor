"""Create, privately upload, and automatically remove a temporary test video."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from src.youtube.auth import YouTubeAuthenticationError
from src.youtube.upload import upload_video


def main() -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="macca-youtube-smoke-") as temp:
            video = Path(temp) / "oauth-smoke-test.mp4"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                 "-i", "color=c=0x171022:s=720x1280:r=30:d=4", "-vf",
                 "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Macca YouTube private test':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=(h-text_h)/2",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)],
                check=True,
            )
            result = upload_video(
                video,
                title="Macca the Gator - Private YouTube OAuth Test",
                description="Private test upload validating YouTube OAuth and resumable upload. This temporary test video may be deleted after verification.",
                tags=["Macca the Gator", "private test"],
                privacy_status="private",
            )
    except YouTubeAuthenticationError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except Exception:
        print("Private YouTube smoke-test upload failed; temporary files were removed.")
        raise SystemExit(1) from None
    print(f"Private smoke-test upload completed: {result['url']}")


if __name__ == "__main__":
    main()
