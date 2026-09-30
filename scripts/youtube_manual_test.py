"""Manually verify the configured YouTube OAuth account without uploading."""

from __future__ import annotations

from src.youtube.auth import YouTubeAuthenticationError
from src.youtube.auth import credentials_from_environment


def main() -> None:
    try:
        credentials = credentials_from_environment()
    except YouTubeAuthenticationError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except Exception:
        print("YouTube authentication verification failed.")
        raise SystemExit(1) from None
    if not credentials.token:
        print("YouTube access token refresh returned no access token.")
        raise SystemExit(1)
    print("OAuth access token refreshed successfully for the youtube.upload scope.")


if __name__ == "__main__":
    main()
