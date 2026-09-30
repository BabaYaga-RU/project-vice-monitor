"""Manually verify the configured YouTube OAuth account without uploading."""

from __future__ import annotations

import json

from src.youtube.auth import YouTubeAuthenticationError
from src.youtube.upload import authenticated_channel, build_youtube_service


def main() -> None:
    try:
        channel = authenticated_channel(build_youtube_service())
    except YouTubeAuthenticationError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except Exception as exc:
        # Avoid exception details, which can include remote request diagnostics.
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status == 403:
            print("YouTube API could not inspect the channel; verify API access and OAuth scope.")
        else:
            print("YouTube authentication/channel verification failed.")
        raise SystemExit(1) from None
    print(json.dumps({"authenticated": True, "channel_id": channel["id"], "channel_title": channel["title"]}))


if __name__ == "__main__":
    main()
