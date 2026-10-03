# Macca social video pipeline

## Rendering

`src/youtube/shorts.py` renders one shared vertical MP4 from article data already stored in `blog/posts.json`; it does not call an AI service at render time. Kokoro is the primary local narrator and eSpeak NG remains the fallback. The first spoken line is the story hook/title rather than generic channel branding. Output is H.264/AAC at 1080x1920/30 FPS and is constrained to 15–20 seconds. The same module also generates an original 1280x720 YouTube thumbnail. The CTA points viewers to Macca Blog through the profile/channel links.

The GitHub Actions workflow renders each queued article once into `$RUNNER_TEMP/macca-social-videos`. YouTube reuses that file. Instagram reuses it as a Reel when R2 staging and the Facebook Login/Page-token API path are available. If a Reel cannot be prepared, the queue item is retained for retry instead of falling back to an image post. Temporary runner files are not committed.

To roll back YouTube rendering while validating, set the GitHub repository variable `SHORTS_RENDERER` to `legacy`. Unset it (or set it to `narrated`) to use the new renderer. In legacy mode Instagram continues with its square image.

## Optional licensed music

Put only licensed tracks in `assets/audio/shorts/`. The renderer works with an empty folder. If licensed tracks are present, it selects one and normalizes it to approximately 16 dB below the narration. Set `SHORTS_MUSIC_PATH` for a deterministic local choice.

## Instagram Reels staging

The Meta API collection's documented Reels Publishing flow creates a `media_type=REELS` container using a publicly reachable `video_url`, polls the container, and publishes it with `media_publish`. This code does not assume that local/resumable upload is supported by the current account/token path. It attempts a Reel only when account resolution chose `graph.facebook.com` (Facebook Login/Page token); an Instagram Login token keeps using the established image post.

To enable temporary video URLs:

1. Create a dedicated Cloudflare R2 bucket and enable its public URL/custom domain. Do not use a bucket containing unrelated private files.
2. Set a lifecycle rule to delete objects with prefix `instagram-reels/` after one day. The workflow also deletes the uploaded object after the Instagram publish attempt.
3. Add GitHub Actions secrets `CLOUDFLARE_R2_ACCOUNT_ID`, `CLOUDFLARE_R2_ACCESS_KEY_ID`, `CLOUDFLARE_R2_SECRET_ACCESS_KEY`, `CLOUDFLARE_R2_BUCKET`, and `CLOUDFLARE_R2_PUBLIC_BASE_URL` (the public bucket base URL, without a trailing slash).

R2 provides a free monthly allowance and free egress, but usage above the included allowance can be billed. The public `r2.dev` endpoint is for development; use a custom domain for steady production delivery.

### Hard R2 limits

`blog/r2-upload-usage.json` is the committed quota ledger. It reserves upload attempts before network transfer, so failures or interrupted runners still consume the budget. Retries count against the caps, which is deliberately stricter than counting only completed objects.

- At most one distinct article object per workflow run and one object reservation per article.
- At most 24 R2 PUT attempts in any rolling 24 hours and 750 reserved PUT attempts per UTC calendar month.
- At most two explicit PUT attempts for the same object; SDK-level automatic retries are disabled.
- MP4 files larger than 25 MiB are rejected before R2 transfer.
- Limits are constants in `src/youtube/r2_limits.py`; the workflow never raises them. A blocked upload leaves YouTube's local MP4 untouched and keeps the Instagram item queued for a later Reel retry.
- Cleanup makes up to two delete attempts after Instagram publishing; the one-day bucket lifecycle remains the final fallback if deletion or the runner fails.

## Optional YouTube Analytics

Upload credentials remain in `src/youtube/auth.py` with the existing `youtube.upload` scope. Analytics uses a separate module and the additional GitHub secret `YOUTUBE_ANALYTICS_REFRESH_TOKEN`; no code replaces or modifies `YOUTUBE_REFRESH_TOKEN`.

Authorize a separate long-lived OAuth refresh token for the same Google user with `https://www.googleapis.com/auth/yt-analytics.readonly`, using the existing client ID and client secret. Add it as `YOUTUBE_ANALYTICS_REFRESH_TOKEN`. The hourly `youtube-metrics.yml` workflow stores dated cumulative samples, per-day rows, and audience-retention snapshots under `blog/youtube-metrics.json`. After at least 20 usable social-performance observations exist, the blog's topic ranking applies a bounded historical-performance bonus so tiny early samples cannot dominate editorial selection.

YouTube Analytics reports the main content metrics by calendar date, so the collector no longer labels them as exact rolling 6h/24h/72h measurements. Audience retention is collected separately at roughly 24 and 72 hours with `elapsedVideoTimeRatio`, `audienceWatchRatio`, and relative retention when the API has data. Extreme rewatch/reporting outliers are flagged and excluded from automatic learning.

## Safe local render test

Run `python -m unittest discover -s tests -p 'test_shorts.py' -v`. The test uses Windows speech locally when available, or a non-publishing test audio stub elsewhere, writes its MP4 under a temporary directory, and checks codec, resolution, frame rate, audio, and duration. It does not invoke Instagram or YouTube APIs.


## Instagram performance feedback

`.github/workflows/instagram-metrics.yml` collects aggregate Reel insights every six hours when the existing professional-account token permits the requested metrics. Samples are written to `blog/instagram-metrics.json`. The blog topic scorer can combine those aggregate results with YouTube performance only after the minimum sample threshold is met.

## Weekly long-form recap

`.github/workflows/youtube-weekly.yml` publishes one horizontal weekly recap from recent Macca Blog stories. It uses the existing local narration stack and original Macca artwork. The description contains direct article URLs, which gives the channel a clickable path back to Macca Blog that Shorts descriptions cannot reliably provide.
