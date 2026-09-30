"""Build short-lived YouTube API credentials from GitHub Actions secrets."""

from __future__ import annotations

import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

TOKEN_URI = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class YouTubeAuthenticationError(RuntimeError):
    """Raised when persistent OAuth credentials cannot authorize YouTube."""


def credentials_from_environment() -> Credentials:
    """Refresh the access token using the persistent OAuth refresh token."""
    names = (
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
    )
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise YouTubeAuthenticationError(
            "Missing required GitHub Actions secret(s): " + ", ".join(missing)
        )

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=[YOUTUBE_UPLOAD_SCOPE],
    )
    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        # Never include the exception text: OAuth errors can contain request data.
        if "invalid_grant" in str(exc).lower():
            raise YouTubeAuthenticationError(
                "YOUTUBE_REFRESH_TOKEN was revoked or invalidated; upload stopped."
            ) from None
        raise YouTubeAuthenticationError(
            "YouTube access token refresh failed; upload stopped."
        ) from None
    except Exception:
        raise YouTubeAuthenticationError(
            "YouTube access token refresh failed; upload stopped."
        ) from None
    return credentials
