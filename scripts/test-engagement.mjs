#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const root=process.cwd();
const posts=JSON.parse(await fs.readFile(path.join(root,'blog','posts.json'),'utf8'));
assert.ok(Array.isArray(posts) && posts.length>=2,'Need at least two posts to test recirculation');

const home=await fs.readFile(path.join(root,'blog','index.html'),'utf8');
assert.match(home,/id="trending-title">Trending coverage</,'Home should render the highlighted stories block');
assert.match(home,/class="trending-grid"/,'Home should render the highlighted stories grid');

const first=posts[0];
const article=await fs.readFile(path.join(root,'blog',first.slug,'index.html'),'utf8');
assert.match(article,/data-macca-current-slug=/,'Article should identify its current slug');
assert.match(article,/\/blog\/assets\/engagement\.js/,'Article should load engagement.js');
assert.match(article,/class="article-related"/,'Article should render related stories at the end');
assert.match(article,/data-next-story-peek/,'Article should render the next-story prompt');
assert.match(article,/data-continuous-sentinel/,'Article should render the continuous-reading sentinel');

const client=await fs.readFile(path.join(root,'blog','assets','engagement.js'),'utf8');
assert.match(client,/IntersectionObserver/,'Continuous reading should be viewport-driven');
assert.match(client,/fetch\('\/blog\/posts\.json'/,'Continuous reading should use the canonical post index');
assert.doesNotMatch(client,/window\.open|target\s*=\s*['"]_blank/,'Recirculation must not open hidden/new tabs');

console.log('Engagement UI checks passed.');
