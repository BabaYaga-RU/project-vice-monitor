#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';

const ROOT = process.cwd();
const GRAPH_VERSION = 'v23.0';
const PUBLISHED_FILE = process.env.INSTAGRAM_PUBLISHED_FILE || path.join(ROOT, 'blog', 'instagram-published.json');
const METRICS_FILE = process.env.INSTAGRAM_METRICS_FILE || path.join(ROOT, 'blog', 'instagram-metrics.json');
const token = process.env.INSTAGRAM_ACCESS_TOKEN || '';

const readJson = async (file, fallback) => {
  try { return JSON.parse(await fs.readFile(file, 'utf8')); }
  catch { return fallback; }
};
const writeJson = async (file, value) => {
  await fs.mkdir(path.dirname(file), {recursive:true});
  await fs.writeFile(file, JSON.stringify(value, null, 2) + '\n', 'utf8');
};

async function insightGroup(mediaId, metrics) {
  const url = new URL(`https://graph.facebook.com/${GRAPH_VERSION}/${mediaId}/insights`);
  url.searchParams.set('metric', metrics.join(','));
  url.searchParams.set('access_token', token);
  const response = await fetch(url, {signal:AbortSignal.timeout(20000)});
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.error) {
    const message = body.error?.message || `HTTP ${response.status}`;
    throw new Error(message);
  }
  const values = {};
  for (const item of body.data || []) {
    const value = item.values?.[0]?.value ?? item.total_value?.value ?? item.value;
    if (item.name && value !== undefined) values[item.name] = value;
  }
  return values;
}

async function collect() {
  if (!token) throw new Error('INSTAGRAM_ACCESS_TOKEN is not configured.');
  const published = await readJson(PUBLISHED_FILE, {});
  const store = await readJson(METRICS_FILE, {schemaVersion:1, media:{}});
  store.schemaVersion = 1;
  store.media ||= {};
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  let changes = 0;

  for (const [publicationKey, record] of Object.entries(published || {})) {
    const articleUrl = record?.articleUrl || publicationKey.split('::')[0];
    const mediaId = record?.mediaId;
    if (!mediaId || record?.mediaType !== 'REELS') continue;
    const entry = store.media[mediaId] ||= {
      articleUrl,
      permalink: record.permalink || '',
      publishedAt: record.publishedAt || '',
      mediaType: 'REELS',
      samples: [],
    };
    if ((entry.samples || []).some(sample => sample.collectedDate === today)) continue;

    const merged = {};
    const groups = [
      ['views', 'reach', 'total_interactions'],
      ['likes', 'comments', 'saved', 'shares'],
      ['ig_reels_avg_watch_time', 'ig_reels_video_view_total_time'],
    ];
    for (const group of groups) {
      try { Object.assign(merged, await insightGroup(mediaId, group)); }
      catch (error) { console.warn(`Instagram insights group ${group.join(',')} unavailable for ${mediaId}: ${error.message}`); }
    }
    if (!Object.keys(merged).length) {
      console.log(`No Instagram Reel insights available yet for ${mediaId}; it will be retried.`);
      continue;
    }

    const publishedAt = Date.parse(record.publishedAt || '');
    const actualAgeHours = Number.isFinite(publishedAt) ? Math.max(0, (Date.now() - publishedAt) / 3600000) : null;
    entry.permalink = record.permalink || entry.permalink;
    entry.publishedAt = record.publishedAt || entry.publishedAt;
    entry.samples ||= [];
    entry.samples.push({
      collectedDate: today,
      collectedAt: now.toISOString(),
      actualAgeHours: actualAgeHours == null ? null : Math.round(actualAgeHours * 10) / 10,
      metrics: merged,
    });
    changes += 1;
  }

  await writeJson(METRICS_FILE, store);
  console.log(`Saved ${changes} Instagram Reel insight sample(s).`);
}

await collect();
