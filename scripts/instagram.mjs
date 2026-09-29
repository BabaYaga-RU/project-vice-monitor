#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';

const ROOT = process.cwd();
const BASE = (process.env.SITE_URL || 'https://macca-lab.onrender.com').replace(/\/$/, '');
const GRAPH_VERSION = 'v23.0';
const QUEUE_FILE = process.env.INSTAGRAM_QUEUE_FILE || path.join(ROOT, 'blog', 'instagram-queue.json');
const POSTS_FILE = path.join(ROOT, 'blog', 'posts.json');
const PUBLISHED_FILE = path.join(ROOT, 'blog', 'instagram-published.json');
const token = process.env.INSTAGRAM_ACCESS_TOKEN;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const safeJson = async (file, fallback) => { try { return JSON.parse(await fs.readFile(file, 'utf8')); } catch { return fallback; } };
const saveJson = async (file, value) => { await fs.mkdir(path.dirname(file), {recursive:true}); await fs.writeFile(file, JSON.stringify(value, null, 2) + '\n'); };

function imageConverter() {
  for (const cmd of ['magick', 'convert']) {
    const result = spawnSync(cmd, ['-version'], {encoding:'utf8'});
    if (!result.error && result.status === 0) return cmd;
  }
  throw new Error('ImageMagick is required. Install it before preparing Instagram images.');
}

function wrapTitle(value, max = 25, maxLines = 3) {
  const words = String(value || 'GTA news').replace(/\s+/g, ' ').trim().split(' ');
  const lines = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (next.length > max && line) { lines.push(line); line = word; }
    else line = next;
  }
  if (line) lines.push(line);
  if (lines.length > maxLines) {
    lines.length = maxLines;
    lines[maxLines - 1] = `${lines[maxLines - 1].replace(/[.,:;!?]+$/, '')}…`;
  }
  return lines;
}

async function downloadImage(url, dest) {
  if (!/^https:\/\//i.test(url || '')) return false;
  try {
    const response = await fetch(url, {headers:{'user-agent':'MaccaBlogInstagram/1.0'}, signal:AbortSignal.timeout(20000)});
    if (!response.ok || !/^image\//i.test(response.headers.get('content-type') || '')) return false;
    const data = Buffer.from(await response.arrayBuffer());
    if (!data.length || data.length > 15 * 1024 * 1024) return false;
    await fs.writeFile(dest, data);
    return true;
  } catch (error) {
    console.warn(`Article image unavailable; using Macca artwork: ${error.message}`);
    return false;
  }
}

function renderCard(command, input, output, title) {
  const args = [input, '-auto-orient', '-resize', '1080x1080^', '-gravity', 'center', '-background', '#190d25', '-extent', '1080x1080', '-flatten',
    '-fill', 'rgba(9,6,18,0.80)', '-draw', 'rectangle 0,570 1080,1080',
    '-fill', '#00f3ff', '-draw', 'roundrectangle 72,630 150,640 5,5',
    '-font', 'DejaVu-Sans-Bold', '-pointsize', '27', '-fill', '#00f3ff', '-annotate', '+72+700', 'MACCA BLOG  •  GTA NEWS',
    '-font', 'DejaVu-Sans-Bold', '-pointsize', '58', '-fill', '#ffffff'];
  const lines = wrapTitle(title);
  lines.forEach((line, index) => args.push('-annotate', `+72+${790 + index * 77}`, line));
  args.push('-font', 'DejaVu-Sans', '-pointsize', '23', '-fill', '#f4e9fa', '-annotate', '+72+1034', 'Read the full story at macca-lab.onrender.com', '-strip', '-quality', '88', '-sampling-factor', '4:2:0', output);
  const result = spawnSync(command, args, {encoding:'utf8', maxBuffer:2*1024*1024});
  if (result.error || result.status !== 0) throw new Error(`Could not compose Instagram artwork: ${result.error?.message || result.stderr || `exit ${result.status}`}`);
}

async function prepare() {
  const queue = await safeJson(QUEUE_FILE, []);
  if (!Array.isArray(queue) || !queue.length) { console.log('No new articles to prepare for Instagram.'); return; }
  const posts = await safeJson(POSTS_FILE, []);
  const pending = [];
  for (const item of queue) {
    try { await fs.access(path.join(ROOT, 'blog', item.slug, 'instagram.jpg')); }
    catch { pending.push(item); }
  }
  if (!pending.length) { console.log('All queued Instagram images already exist.'); return; }
  const command = imageConverter();
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'macca-instagram-'));
  try {
    for (const {slug} of pending) {
      const post = posts.find(item => item.slug === slug);
      if (!post) throw new Error(`Instagram queue references missing blog article: ${slug}`);
      const localInput = path.join(tempDir, 'article-image');
      const fromArticle = await downloadImage(post.thumbnail || post.inlineImages?.[0]?.url, localInput);
      const input = fromArticle ? localInput : path.join(ROOT, 'ads', 'partner.webp');
      const output = path.join(ROOT, 'blog', slug, 'instagram.jpg');
      await fs.mkdir(path.dirname(output), {recursive:true});
      renderCard(command, input, output, post.title);
      console.log(`Prepared ${output} (${fromArticle ? 'article image' : 'Macca artwork'} + title).`);
    }
  } finally { await fs.rm(tempDir, {recursive:true, force:true}); }
}

async function graphGet(host, resource, fields) {
  const url = new URL(`https://${host}/${GRAPH_VERSION}/${resource}`);
  if (fields) url.searchParams.set('fields', fields);
  const response = await fetch(url, {headers:{authorization:`Bearer ${token}`}, signal:AbortSignal.timeout(20000)});
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.error) {
    const error = body.error;
    throw new Error(`${error?.message || `Meta Graph API returned HTTP ${response.status}`}${error?.code ? ` (code ${error.code}${error.error_subcode ? `, subcode ${error.error_subcode}` : ''})` : ''}`);
  }
  return body;
}

async function resolveAccount() {
  try {
    const user = await graphGet('graph.instagram.com', 'me', 'user_id,username');
    const id = user.user_id || user.id;
    if (id) return {host:'graph.instagram.com', id, username:user.username || ''};
  } catch (error) { console.log(`Instagram Login token check: ${error.message}`); }
  try {
    const pages = await graphGet('graph.facebook.com', 'me/accounts', 'id,name,instagram_business_account{id,username}');
    for (const page of pages.data || []) {
      if (page.instagram_business_account?.id) return {host:'graph.facebook.com', id:page.instagram_business_account.id, username:page.instagram_business_account.username || ''};
    }
  } catch (error) { console.log(`Facebook Login token check: ${error.message}`); }
  throw new Error('Could not resolve a professional Instagram account from INSTAGRAM_ACCESS_TOKEN. Confirm account type, token validity, linked Facebook Page when applicable, and publishing permissions.');
}

async function graphPost(host, resource, params) {
  const response = await fetch(`https://${host}/${GRAPH_VERSION}/${resource}`, {
    method:'POST', headers:{'content-type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({...params, access_token:token}), signal:AbortSignal.timeout(30000)
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.error) {
    const error = body.error;
    throw new Error(`${error?.message || `Meta Graph API returned HTTP ${response.status}`}${error?.code ? ` (code ${error.code}${error.error_subcode ? `, subcode ${error.error_subcode}` : ''})` : ''}`);
  }
  return body;
}

function caption(post) {
  const firstParagraph = post.sections?.flatMap(section => section.paragraphs || []).find(Boolean) || '';
  const secondParagraph = post.sections?.flatMap(section => section.paragraphs || []).filter(Boolean)[1] || '';
  const summary = [post.description, firstParagraph, secondParagraph].filter(Boolean).join('\n\n').slice(0, 1500);
  const link = `${BASE}/blog/${encodeURIComponent(post.slug)}/`;
  const hashtags = '#GTA6 #GrandTheftAuto #RockstarGames #GTAOnline #GTANews #MaccaTheGator';
  return `${summary}\n\nRead the full story: ${link}\n\n${hashtags}`.slice(0, 2200);
}

async function waitForPublicImage(url) {
  for (let attempt = 1; attempt <= 30; attempt++) {
    try {
      const response = await fetch(url, {method:'HEAD', redirect:'follow', signal:AbortSignal.timeout(15000)});
      if (response.ok && /^image\/jpeg/i.test(response.headers.get('content-type') || '')) return;
      console.log(`Waiting for deployed Instagram image (${attempt}/30, HTTP ${response.status || 'unknown'}).`);
    } catch { console.log(`Waiting for deployed Instagram image (${attempt}/30).`); }
    await delay(10000);
  }
  throw new Error(`The public JPEG did not become available: ${url}`);
}

async function waitForContainer(host, containerId) {
  let status = null;
  for (let attempt = 1; attempt <= 30; attempt++) {
    const result = await graphGet(host, containerId, 'status_code,status');
    status = result.status_code;
    if (status === 'FINISHED') return;
    if (status === 'ERROR' || status === 'EXPIRED') throw new Error(`Instagram media processing ended with ${status}: ${result.status || 'no further details'}`);
    console.log(`Waiting for Instagram media processing (${attempt}/30, ${status || 'pending'}).`);
    await delay(5000);
  }
  throw new Error(`Instagram media container did not finish processing (last status: ${status || 'unknown'}).`);
}

async function inspectQueue() {
  const queue = await safeJson(QUEUE_FILE, []);
  if (!Array.isArray(queue)) throw new Error('blog/instagram-queue.json must contain a JSON array.');
  let needsArtwork = false;
  for (const {slug} of queue) {
    try { await fs.access(path.join(ROOT, 'blog', slug, 'instagram.jpg')); }
    catch { needsArtwork = true; break; }
  }
  if (process.env.GITHUB_OUTPUT) await fs.appendFile(process.env.GITHUB_OUTPUT, `needs_artwork=${needsArtwork ? 'true' : 'false'}\n`);
  console.log(`${queue.length} article(s) pending on Instagram; new artwork ${needsArtwork ? 'is' : 'is not'} required.`);
}

async function findExisting(host, accountId, storyUrl, published) {
  if (published[storyUrl]) return published[storyUrl];
  try {
    const media = await graphGet(host, `${accountId}/media`, 'id,caption,permalink,timestamp');
    return (media.data || []).find(item => item.caption?.includes(storyUrl)) || null;
  } catch (error) {
    console.warn(`Could not check recent Instagram posts before publishing: ${error.message}`);
    return null;
  }
}

async function publish() {
  const queue = await safeJson(QUEUE_FILE, []);
  if (!Array.isArray(queue) || !queue.length) { console.log('No new articles to publish to Instagram.'); return; }
  if (!token) throw new Error('INSTAGRAM_ACCESS_TOKEN is not configured in GitHub Actions secrets.');
  const posts = await safeJson(POSTS_FILE, []);
  const published = await safeJson(PUBLISHED_FILE, {});
  const account = await resolveAccount();
  if (account.username) console.log(`Instagram account resolved: @${account.username}`);
  for (const {slug} of queue) {
    const post = posts.find(item => item.slug === slug);
    if (!post) throw new Error(`Instagram queue references missing blog article: ${slug}`);
    const storyUrl = `${BASE}/blog/${encodeURIComponent(slug)}/`;
    const imageUrl = `${BASE}/blog/${encodeURIComponent(slug)}/instagram.jpg`;
    await waitForPublicImage(imageUrl);
    const existing = await findExisting(account.host, account.id, storyUrl, published);
    if (existing) {
      published[storyUrl] = {mediaId:existing.mediaId || existing.id, permalink:existing.permalink || '', publishedAt:existing.publishedAt || existing.timestamp || new Date().toISOString()};
      console.log(`Already present on Instagram; recording ${storyUrl}`);
      await saveJson(PUBLISHED_FILE, published);
      const remaining = queue.filter(item => item.slug !== slug);
      await saveJson(QUEUE_FILE, remaining);
      queue.splice(0, queue.length, ...remaining);
      continue;
    }
    const container = await graphPost(account.host, `${account.id}/media`, {image_url:imageUrl, caption:caption(post), alt_text:post.title});
    if (!container.id) throw new Error('Meta did not return a media container ID.');
    await waitForContainer(account.host, container.id);
    const media = await graphPost(account.host, `${account.id}/media_publish`, {creation_id:container.id});
    if (!media.id) throw new Error('Meta did not return a published media ID.');
    let permalink = '';
    try { permalink = (await graphGet(account.host, media.id, 'permalink')).permalink || ''; } catch {}
    published[storyUrl] = {mediaId:media.id, permalink, publishedAt:new Date().toISOString()};
    await saveJson(PUBLISHED_FILE, published);
    const remaining = queue.filter(item => item.slug !== slug);
    await saveJson(QUEUE_FILE, remaining);
    queue.splice(0, queue.length, ...remaining);
    console.log(`Published ${slug} to Instagram (${media.id})${permalink ? `: ${permalink}` : ''}`);
  }
}

const command = process.argv[2];
if (command === 'prepare') await prepare();
else if (command === 'inspect') await inspectQueue();
else if (command === 'publish') await publish();
else throw new Error('Usage: node scripts/instagram.mjs <inspect|prepare|publish>');
