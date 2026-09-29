# Site advertisements

The shared ad runtime and configuration live here so pages across the site can use the same system. Ads currently appear only on `/blog/` and article pages.

- `ads.js` mounts placements marked with `data-ad-slot` when a page includes `/ads/ads.js`.
- `config.json` maps placement names to enabled advertisements.
- `banners/` contains the reusable SVG banners.
- `partner.webp` is the optimized artwork used in those banners.

To add a placement to a page, add an element such as `<div class="ad-slot" data-ad-slot="sidebar" aria-label="Advertisement"></div>` and load the shared script there. The script is not included site-wide, so pages without a placement remain ad-free.
