# Macca social video pipeline

## Rendering

`src/youtube/shorts.py` now renders one shared vertical MP4 from the article already in `blog/posts.json`. It uses the existing title, description, article paragraphs, and available article image; it does not call an AI service. eSpeak NG provides local English narration in GitHub Actions. FFmpeg applies slow image movement, animated phrase captions, AAC audio, and H.264 output at 1080x1920/30 FPS. The duration is checked against 15–25 seconds. A short CTA points viewers to the Macca Blog.

The GitHub Actions workflow renders each queued article once into `$RUNNER_TEMP/macca-social-videos`. YouTube reuses that file. Instagram can reuse it as a Reel only when R2 staging and the Facebook Login/Page-token API path are available; otherwise the existing square-image publication remains the fallback. Temporary runner files are not committed.

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

## Optional YouTube Analytics

Upload credentials remain in `src/youtube/auth.py` with the existing `youtube.upload` scope. Analytics uses a separate module and the additional GitHub secret `YOUTUBE_ANALYTICS_REFRESH_TOKEN`; no code replaces or modifies `YOUTUBE_REFRESH_TOKEN`.

Authorize a separate long-lived OAuth refresh token for the same Google user with `https://www.googleapis.com/auth/yt-analytics.readonly`, using the existing client ID and client secret. Add it as `YOUTUBE_ANALYTICS_REFRESH_TOKEN`. The hourly `youtube-metrics.yml` workflow then stores views, engaged views, average view duration/percentage, likes, comments, shares, and subscribers gained under `blog/youtube-metrics.json`. The data does not affect topic selection yet.

YouTube Analytics returns these content metrics at calendar-day granularity. Each requested 6h/24h/72h snapshot therefore records the UTC calendar date range and a `basis` field; it is not an exact rolling 6-, 24-, or 72-hour measurement. Analytics API data can arrive after the target time, so a milestone with no data is retried on a later hourly run.

## Safe local render test

Run `python -m unittest discover -s tests -p 'test_shorts.py' -v`. The test uses Windows speech locally when available, or a non-publishing test audio stub elsewhere, writes its MP4 under a temporary directory, and checks codec, resolution, frame rate, audio, and duration. It does not invoke Instagram or YouTube APIs.
