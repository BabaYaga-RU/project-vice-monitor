# Render static-site migration

Macca Lab is now prepared to run as a Render Static Site. The current production URL is used in canonical URLs, social metadata, API allowlists and OAuth/social publication records, so the live service must not be deleted or renamed until the replacement static site is verified.

Use `render-static.yaml` to create the preview static service first. After verifying article routes, images, `/social/`, evergreen hubs, `ads.txt`, IndexNow key, Skylet and social links, perform the final Render-side cutover so the canonical production hostname remains stable.

The repository itself does not require a Node/Express process at runtime. GitHub Actions generates and commits the static HTML, feeds, sitemaps and artwork.
