"""Optional credentials for YouTube Analytics, isolated from upload OAuth."""

from __future__ import annotations

import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .auth import TOKEN_URI, YouTubeAuthenticationError

YOUTUBE_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"


def analytics_credentials_from_environment() -> Credentials:
    """Use the separate analytics refresh token; never change upload auth."""
    names = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_ANALYTICS_REFRESH_TOKEN")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise YouTubeAuthenticationError("Missing analytics credential(s): " + ", ".join(missing))
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_ANALYTICS_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=[YOUTUBE_ANALYTICS_SCOPE],
    )
    try:
        credentials.refresh(Request())
    except RefreshError as exc:
        if "invalid_grant" in str(exc).lower():
            raise YouTubeAuthenticationError("YOUTUBE_ANALYTICS_REFRESH_TOKEN is invalid or revoked.") from None
        raise YouTubeAuthenticationError("YouTube Analytics access token refresh failed.") from None
    except Exception:
        raise YouTubeAuthenticationError("YouTube Analytics access token refresh failed.") from None
    return credentials
