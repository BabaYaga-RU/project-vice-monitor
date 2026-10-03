#!/usr/bin/env node
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';

const read = path => fs.readFile(path, 'utf8');

const [adsTxt, blog, seo, ads, instagram, queue, shorts, ytMetrics, ytWorkflow, igWorkflow, weeklyWorkflow] = await Promise.all([
  read('ads.txt'),
  read('scripts/blog.mjs'),
  read('scripts/build-seo.mjs'),
  read('ads/ads.js'),
  read('scripts/instagram.mjs'),
  read('scripts/youtube_queue.py'),
  read('src/youtube/shorts.py'),
  read('scripts/youtube_metrics.py'),
  read('.github/workflows/youtube-metrics.yml'),
  read('.github/workflows/instagram-metrics.yml'),
  read('.github/workflows/youtube-weekly.yml'),
]);

assert.match(adsTxt, /google\.com, pub-7821352420515145, DIRECT, f08c47fec0942fa0/);
for (const source of [blog, seo]) {
  assert.match(source, /ca-pub-7821352420515145/);
  assert.doesNotMatch(source, /ca-pub-1038995366418919/);
}

assert.match(blog, /youtubeTitle/);
assert.match(blog, /socialHook/);
assert.match(blog, /instagramCaptionLead/);
assert.match(blog, /seoTitle/);
assert.match(blog, /seoDescription/);
assert.match(blog, /NewsArticle/);
assert.match(blog, /BreadcrumbList/);
assert.match(blog, /news-sitemap\.xml/);
assert.match(seo, /blog\/news-sitemap\.xml/);
assert.match(blog, /observations\.length<20/);
assert.match(blog, /historicalPerformanceBonus/);
assert.match(blog, /data-ad-context/);

assert.match(ads, /contextText/);
assert.match(ads, /affinity = ad/);
assert.match(ads, /contextualAd/);
assert.match(ads, /AFFILIATE_SESSION_KEY/);
assert.match(ads, /sessionStorage/);
assert.match(ads, /recordAffiliateEvent/);

assert.doesNotMatch(shorts, /Rockstar fans, here is the latest story/);
assert.match(shorts, /Full story .*Macca Blog\. Link on profile\./);
assert.match(shorts, /def create_thumbnail/);

assert.match(queue, /def youtube_title/);
assert.match(queue, /def youtube_tags/);
assert.match(queue, /set_thumbnail/);
assert.match(queue, /#RockstarGames/);

assert.match(instagram, /retaining the item in the Instagram queue for retry/);
assert.doesNotMatch(instagram, /image_url:imageUrl/);
assert.match(instagram, /share_to_feed:'false'/);

assert.match(ytMetrics, /dimensions="day"/);
assert.match(ytMetrics, /elapsedVideoTimeRatio/);
assert.match(ytMetrics, /audienceWatchRatio/);
assert.match(ytWorkflow, /daily performance and retention/i);
assert.match(igWorkflow, /Collect Instagram Reel metrics/);
assert.match(weeklyWorkflow, /Macca weekly YouTube recap/);

console.log('Growth pipeline checks passed.');
