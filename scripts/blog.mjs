#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

const ROOT = process.cwd();
const BASE = process.env.SITE_URL || 'https://macca-lab.onrender.com';
const BACKFILL = process.argv.includes('--backfill');
const FEEDS = [
  'https://news.google.com/rss/search?q=GTA+6+news+rumors+leaks+trailer+release+date+preorder+price+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=GTA+Online+Rockstar+update+event+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=Rockstar+Games+news+lawsuit+studio+hack+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=Take-Two+Interactive+news+lawsuit+game+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=site%3Areddit.com%2Fr%2FGTA+OR+site%3Agtaforums.com+Grand+Theft+Auto+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  // Public X posts are discovered through Google News RSS; this needs no X API credential.
  'https://news.google.com/rss/search?q=site%3Ax.com%2FGTA6Alerts+GTA+OR+Rockstar+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=site%3Ax.com%2FGTAVI_Countdown+GTA+OR+Rockstar+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=site%3Ax.com%2FGTABase+GTA+OR+Rockstar+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=site%3Ax.com%2FRockstarINTEL+GTA+OR+Rockstar+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://news.google.com/rss/search?q=site%3Ax.com%2FRockstarGames+GTA+OR+Rockstar+when%3A21d&hl=en-US&gl=US&ceid=US%3Aen',
  'https://flowgames.gg/feed/',
  'https://rockstarintel.com/feed/',
  'https://feeds.feedburner.com/ign/gta',
  'https://www.pcgamer.com/rss/',
  'https://www.gamespot.com/feeds/news/',
  'https://www.eurogamer.net/feed',
  'https://kotaku.com/rss',
  'https://www.videogameschronicle.com/feed/',
  'https://www.rockpapershotgun.com/feed'
];
const DATA_FILE = path.join(ROOT, 'blog', 'posts.json');
const HISTORY_FILE = path.join(ROOT, 'blog', 'history.json');
const MONITOR_STATE_FILE = path.join(ROOT, 'blog', 'monitor-state.json');
const CANDIDATE_FILE = path.join(process.env.RUNNER_TEMP || os.tmpdir(), 'macca-blog-candidate.json');
let successfulFeedReads = 0;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const slugify = s => s.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,80) || 'gta-story';
const strip = s => s.replace(/<[^>]*>/g,' ').replace(/&amp;/g,'&').replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/\s+/g,' ').trim();
const usefulImage = value => { try { const u=new URL(value); return u.protocol==='https:' && !/(^|\.)(googleusercontent\.com|gstatic\.com|google\.com)$/i.test(u.hostname) && !/news\.google\.com$/i.test(u.hostname) ? u.href : ''; } catch { return ''; } };
const adMarkup = () => `<a class="ad-creative" href="https://pklavc.com/blog" target="_blank" rel="sponsored noopener"><span class="ad-copy"><span class="ad-kicker">MACCA BLOG PRESENTS</span><strong>THE PKLAVC BLOG</strong><span class="ad-description">Technology, engineering, open-source projects, and more. Read the blog.</span></span><span class="ad-art"><img src="/ads/partner.webp" alt="Macca partner artwork" loading="lazy"></span></a>`;
const instagramMarkup = () => `<a class="footer-social" href="https://www.instagram.com/macca_the_gator_oficial/" target="_blank" rel="me noopener noreferrer" aria-label="Instagram: Macca the Gator Oficial"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="18" cy="6" r="1.2" fill="currentColor"/></svg><span>Instagram</span></a>`;
const youtubeMarkup = () => `<a class="footer-social" href="https://www.youtube.com/@macca_the_gator_oficial" target="_blank" rel="me noopener noreferrer" aria-label="YouTube: Macca the Gator Oficial"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.6 3.6 12 3.6 12 3.6s-7.6 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.8.5 9.4.5 9.4.5s7.6 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.3 3.6-6.3 3.6Z"/></svg><span>YouTube</span></a>`;
const socialLinksMarkup = () => `${instagramMarkup()}${youtubeMarkup()}`;
const footerMarkup = () => `<footer><div class="footer-about"><a href="/blog/">Macca Blog</a><span>Independent coverage, linked to its sources.</span></div><nav class="footer-links" aria-label="Footer navigation"><a href="/blog/">Home</a><a href="/blog/">Macca Blog</a><a href="/about/">About</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy Policy</a><a href="/blog/feed.xml">RSS</a></nav><div class="footer-socials">${socialLinksMarkup()}</div><p class="footer-disclaimer">Macca Lab is an independent project and is not affiliated with or endorsed by Rockstar Games or Take-Two Interactive.</p></footer>`;
const ADSENSE_SCRIPT = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1038995366418919" crossorigin="anonymous"></script>';

async function readJson(file, fallback) { try { return JSON.parse(await fs.readFile(file,'utf8')); } catch { return fallback; } }
async function writeJson(file, data) { await fs.mkdir(path.dirname(file),{recursive:true}); await fs.writeFile(file, JSON.stringify(data,null,2)+'\n'); }

async function readFeed(url) {
  try {
    const res=await fetch(url,{headers:{'user-agent':'GTA-Blog-Research/1.0'},signal:AbortSignal.timeout(12000)});
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    successfulFeedReads++;
    const xml=await res.text(), items=[];
    for(const m of xml.matchAll(/<(item|entry)\b[\s\S]*?<\/\1>/gi)) {
      const block=m[0];
      const get=tag=>strip(block.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`,'i'))?.[1]?.replace(/<!\[CDATA\[|\]\]>/g,'' )||'');
      const title=get('title');
      const link=get('link') || block.match(/<link[^>]+href=["']([^"']+)/i)?.[1] || '';
      const description=get('description') || get('summary') || get('content');
      const date=get('pubDate') || get('published') || get('updated');
      const publisher=strip(block.match(/<source[^>]*>([\s\S]*?)<\/source>/i)?.[1]?.replace(/<!\[CDATA\[|\]\]>/g,'')||'') || new URL(url).hostname;
      if(title && /^https?:/.test(link)) items.push({title:title.replace(/\s+-\s+[^-]+$/,''),link,description,date,source:publisher});
    }
    return items;
  } catch(e) { console.warn(`Research source unavailable: ${url}: ${e.message}`); return []; }
}

async function research({days=BACKFILL?21:7}={}) {
  const items=[];
  // Fetch in small batches so hourly monitoring stays quick without flooding sources.
  for(let i=0;i<FEEDS.length;i+=5) items.push(...(await Promise.all(FEEDS.slice(i,i+5).map(readFeed))).flat());
  const cutoff=Date.now()-1000*60*60*24*days;
  return items.filter(x=>/grand theft auto|\bgta(?:\s*6)?\b|rockstar|take[- ]two/i.test(`${x.title} ${x.description}`) && (!x.date || (Date.parse(x.date)>=cutoff && Date.parse(x.date)<=Date.now()+86400000)));
}

async function fetchArticle(item) {
  try {
    const response=await fetch(item.link,{headers:{'user-agent':'Mozilla/5.0 (compatible; MaccaBlogResearch/1.0)'},redirect:'follow',signal:AbortSignal.timeout(15000)});
    if(!response.ok) return item;
    const html=await response.text();
    const meta=(name)=>html.match(new RegExp(`<meta[^>]+(?:name|property)=["']${name}["'][^>]+content=["']([^"']+)`, 'i'))?.[1] || html.match(new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+(?:name|property)=["']${name}["']`, 'i'))?.[1] || '';
    const title=strip(html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]||'') || item.title;
    const description=strip(meta('og:description')||meta('description')||item.description);
    const rawImage=meta('og:image')||meta('og:image:url')||meta('twitter:image')||meta('twitter:image:src');
    let imageUrl='';
    imageUrl=rawImage?usefulImage(new URL(rawImage,response.url).href):'';
    const paragraphs=[...html.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map(m=>strip(m[1])).filter(t=>t.length>80).slice(0,9);
    return {...item,title,description,imageUrl,excerpt:paragraphs.join('\n\n').slice(0,6500),publisher:item.source||new URL(response.url).hostname,canonical:response.url};
  } catch(e) { console.warn(`Could not fetch article body for ${item.link}: ${e.message}`); return item; }
}

async function ask(prompt) {
  const errors=[];
  const attempts=[];
  if(process.env.GEMINI_API_KEY) attempts.push(['Gemini',async(p)=>{
    const r=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({contents:[{parts:[{text:p}]}],generationConfig:{responseMimeType:'application/json',temperature:0.4}})});
    if(!r.ok) throw new Error(`HTTP ${r.status}`); return (await r.json()).candidates?.[0]?.content?.parts?.[0]?.text;
  }]);
  if(process.env.CLOUDFLARE_API_TOKEN && process.env.CLOUDFLARE_ACCOUNT_ID) attempts.push(['Cloudflare Workers AI',async(p)=>{
    const url=`https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.1-8b-instruct`;
    const r=await fetch(url,{method:'POST',headers:{authorization:`Bearer ${process.env.CLOUDFLARE_API_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:p}]})});
    if(!r.ok) throw new Error(`HTTP ${r.status}`); return (await r.json()).result?.response;
  }]);
  if(process.env.OPENROUTER_API_KEY) attempts.push(['OpenRouter',async(p)=>{
    const r=await fetch('https://openrouter.ai/api/v1/chat/completions',{method:'POST',headers:{authorization:`Bearer ${process.env.OPENROUTER_API_KEY}`,'content-type':'application/json','HTTP-Referer':BASE,'X-Title':'Macca Blog'},body:JSON.stringify({model:'openrouter/auto',messages:[{role:'user',content:p}],response_format:{type:'json_object'}})});
    if(!r.ok) throw new Error(`HTTP ${r.status}`); return (await r.json()).choices?.[0]?.message?.content;
  }]);
  if(!attempts.length) throw new Error('No AI provider credentials configured.');
  for(const [name,call] of attempts) {
    for(let retry=0;retry<2;retry++) try { const out=await call(retry?`${prompt}\n\nFORMAT REMINDER: Return exactly one valid JSON object. Do not write prose or markdown outside it.`:prompt); if(out){parseModel(out);console.log(`Article generated with ${name}${retry?' after format retry':''}`);return out;} throw new Error('Empty response'); } catch(e) { errors.push(`${name}${retry?' retry':''}: ${e.message}`); if(retry===0)console.warn(`${name} returned invalid output; retrying with a strict JSON reminder.`); }
    console.warn(`${name} failed; trying next provider.`);
  }
  throw new Error(`All AI providers failed: ${errors.join('; ')}`);
}

function parseModel(text) {
  const raw=String(text).replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');
  if(/^"?skip"?$/i.test(raw.trim())) return {skip:true,reason:'provider judged the available reporting too thin'};
  const a=raw.indexOf('{'), b=raw.lastIndexOf('}');
  if(a<0||b<a) throw new Error(`Model did not return JSON: ${raw.slice(0,160).replace(/\s+/g,' ')}`);
  return JSON.parse(raw.slice(a,b+1));
}

function articleHtml(p, all) {
  const url=`${BASE}/blog/${p.slug}/`, imagePath='/images/macca-blog-banner.webp', image=new URL(p.image||'/images/macca-blog-banner.jpg',`${BASE}/`).href;
  const adFallback=slot=>adMarkup(slot);
  const related=all.filter(x=>x.slug!==p.slug && (x.category===p.category || x.tags.some(t=>p.tags.includes(t)))).slice(0,4);
  const latest=all.filter(x=>x.slug!==p.slug).slice(0,5);
  const body=(p.sections||[]).map(s=>`<section><h2>${esc(s.heading)}</h2>${(s.paragraphs||[]).map(x=>`<p>${esc(x)}</p>`).join('')}</section>`).join('');
  const inlineImages=(p.inlineImages||[]).filter(x=>/^https:\/\//i.test(x.url||'')).map(x=>`<figure class="source-image"><a href="${esc(x.sourceUrl||p.sourceUrl||'#')}" target="_blank" rel="noopener noreferrer"><img src="${esc(x.url)}" alt="${esc(x.alt||'Image accompanying the source report')}" loading="lazy" referrerpolicy="no-referrer"></a>${x.caption?`<figcaption>${esc(x.caption)}</figcaption>`:''}</figure>`).join('');
  const cards=(items)=>items.length?items.map(x=>`<a class="post-card" href="/blog/${encodeURIComponent(x.slug)}/"><small>${esc(x.category)} · ${esc(x.date)}</small><strong>${esc(x.title)}</strong><span>${esc(x.description)}</span></a>`).join(''):'<p>More stories coming soon.</p>';
  const schema={"@context":"https://schema.org","@type":"Article",headline:p.title,description:p.description,datePublished:p.date,dateModified:p.date,mainEntityOfPage:url,image,author:{"@type":"Organization",name:'Macca Blog'},publisher:{"@type":"Organization",name:'Macca Blog'}};
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(p.title)} | Macca Blog</title><meta name="description" content="${esc(p.description)}"><meta name="robots" content="index, follow, max-image-preview:large"><link rel="canonical" href="${url}"><meta property="og:type" content="article"><meta property="og:title" content="${esc(p.title)}"><meta property="og:description" content="${esc(p.description)}"><meta property="og:image" content="${esc(image)}"><meta property="og:url" content="${url}"><meta property="og:site_name" content="Macca Blog"><meta property="og:locale" content="en_US"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${esc(p.title)}"><meta name="twitter:description" content="${esc(p.description)}"><meta name="twitter:image" content="${esc(image)}"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/images/favicon-32x32.png"><link rel="icon" type="image/png" sizes="16x16" href="/images/favicon-16x16.png"><link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest"><link rel="alternate" type="application/rss+xml" title="Macca Blog RSS" href="${BASE}/blog/feed.xml"><link rel="stylesheet" href="/blog/assets/blog.css"><script type="application/ld+json">${JSON.stringify(schema).replace(/</g,'\\u003c')}</script><link rel="stylesheet" href="/ads/ads.css"><script defer src="/ads/ads.js"></script><link rel="stylesheet" href="/skylet/widget.css?v=20260929.1">${ADSENSE_SCRIPT}</head><body><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav aria-label="Main navigation"><a href="/blog/">Blog</a><a href="/study/">Study</a><a href="/play/">Play</a></nav></header><main class="layout"><article><a class="back" href="/blog/">← All stories</a><figure class="article-hero"><img src="${esc(imagePath)}" alt="${esc(p.imageAlt||'Macca the Gator at sunset in Vice City')}" onerror="this.onerror=null;this.src='/images/macca-blog-banner.jpg'"><figcaption class="hero-copy"><p class="eyebrow">${esc(p.category)} · <time datetime="${esc(p.date)}">${esc(p.date)}</time></p><h1>${esc(p.title)}</h1><p class="hero-dek">${esc(p.description)}</p></figcaption></figure><div class="article-body">${body}${inlineImages}<h2>Sources and notes</h2><p>Claims, reports, leaks and rumors are attributed to their original sources. Unconfirmed information is labeled clearly and should not be read as established fact.</p><ul>${(p.sources||[]).map(s=>`<li><a rel="noopener noreferrer" href="${esc(s.url)}">${esc(s.title)}</a> <span>(${esc(s.publisher||new URL(s.url).hostname)})</span></li>`).join('')}</ul></div><div class="ad-slot" data-ad-slot="article-inline" aria-label="Advertisement">${adFallback('article-inline')}</div></article><aside><section class="side-section"><h2>Latest posts</h2><div class="post-list">${cards(latest)}</div></section><div class="ad-slot" data-ad-slot="sidebar" aria-label="Advertisement">${adFallback('sidebar')}</div><section class="side-section"><h2>Related stories</h2><div class="post-list">${cards(related)}</div></section></aside></main>${footerMarkup()}<script defer src="/skylet/widget.js?v=20260929.1"></script></body></html>`;
}

async function build() {
  const posts=(await readJson(DATA_FILE,[])).sort((a,b)=>b.date.localeCompare(a.date));
  for(const p of posts) {
    p.image='/images/macca-blog-banner.jpg'; p.imageAlt='Macca the Gator at sunset in Vice City';
    const inlineImages=Array.isArray(p.inlineImages)?p.inlineImages:[];
    const thumbnail=String(p.thumbnail||'').replace(/&amp;/g,'&');
    if(/^https:\/\//i.test(thumbnail)&&!inlineImages.some(x=>x.url===thumbnail)) {
      inlineImages.unshift({url:thumbnail,alt:p.thumbnailAlt||p.title,caption:'Image accompanying the source report',sourceUrl:p.sourceUrl||p.sources?.[0]?.url||'#'});
      p.inlineImages=inlineImages;
    }
    await fs.mkdir(path.join(ROOT,'blog',p.slug),{recursive:true}); await fs.writeFile(path.join(ROOT,'blog',p.slug,'index.html'),articleHtml(p,posts));
  }
  await writeJson(DATA_FILE,posts);
  const card=p=>`<a class="feature" href="/blog/${encodeURIComponent(p.slug)}/"><span class="feature-cover"><img src="${esc(p.thumbnail||'/images/macca-blog-banner.webp')}" alt="${esc(p.thumbnailAlt||p.title)}" loading="lazy" onerror="this.onerror=null;this.src='/images/macca-blog-banner.webp'"><span class="cover-label">MACCA BLOG | ${esc(p.category)}</span></span><small>${esc(p.category)} | ${esc(p.date)}</small><h2>${esc(p.title)}</h2><p>${esc(p.description)}</p></a>`;
  const cats=[...new Set(posts.map(p=>p.category))].sort();
  const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Macca Blog | GTA News, History and Analysis</title><meta name="description" content="News, reports, rumors and analysis about Grand Theft Auto, with sources linked and unconfirmed claims clearly labeled."><meta name="robots" content="index, follow, max-image-preview:large"><link rel="canonical" href="${BASE}/blog/"><meta property="og:type" content="website"><meta property="og:site_name" content="Macca Blog"><meta property="og:title" content="Macca Blog | GTA News, History and Analysis"><meta property="og:description" content="News, reports, rumors and analysis about Grand Theft Auto."><meta property="og:url" content="${BASE}/blog/"><meta property="og:image" content="${BASE}/images/macca-blog-banner.jpg"><meta property="og:locale" content="en_US"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Macca Blog"><meta name="twitter:description" content="Sourced reporting and analysis from across the GTA community."><meta name="twitter:image" content="${BASE}/images/macca-blog-banner.jpg"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/images/favicon-32x32.png"><link rel="icon" type="image/png" sizes="16x16" href="/images/favicon-16x16.png"><link rel="apple-touch-icon" sizes="180x180" href="/images/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest"><link rel="alternate" type="application/rss+xml" title="Macca Blog RSS" href="${BASE}/blog/feed.xml"><link rel="stylesheet" href="/blog/assets/blog.css"><script type="application/ld+json">${JSON.stringify({'@context':'https://schema.org','@type':'Blog','name':'Macca Blog','url':`${BASE}/blog/`})}</script><link rel="stylesheet" href="/ads/ads.css"><script defer src="/ads/ads.js"></script><link rel="stylesheet" href="/skylet/widget.css?v=20260929.1">${ADSENSE_SCRIPT}</head><body><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav aria-label="Main navigation"><a href="/blog/">Blog</a><a href="/study/">Study</a><a href="/play/">Play</a></nav></header><main class="home"><section class="intro"><p class="eyebrow">GRAND THEFT AUTO, REPORTED</p><h1>Stories behind the streets.</h1><p>News, reporting, rumors and analysis from across the GTA community. Every story links back to its sources.</p><div class="categories">${cats.map(c=>`<span>${esc(c)}</span>`).join('')}</div></section><div class="ad-slot" data-ad-slot="blog-top" aria-label="Advertisement">${adMarkup()}</div><section><h2>Latest stories</h2><div class="grid">${posts.length?posts.map(card).join(''):'<p>No stories published yet.</p>'}</div></section><section><h2>Featured</h2><div class="grid">${posts.filter(p=>p.featured).map(card).join('')||posts.slice(0,2).map(card).join('')}</div></section></main>${footerMarkup()}<script defer src="/skylet/widget.js?v=20260929.1"></script></body></html>`;
  await fs.writeFile(path.join(ROOT,'blog','index.html'),html);
  const urls=posts.map(p=>`  <url><loc>${BASE}/blog/${esc(p.slug)}/</loc><lastmod>${esc(p.date)}</lastmod></url>`).join('\n');
  await fs.writeFile(path.join(ROOT,'blog','sitemap.xml'),`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>${BASE}/blog/</loc>${posts[0]?.date?`<lastmod>${esc(posts[0].date)}</lastmod>`:''}</url>\n${urls}\n</urlset>\n`);
  const items=posts.slice(0,30).map(p=>`<item><title>${esc(p.title)}</title><link>${BASE}/blog/${esc(p.slug)}/</link><guid isPermaLink="true">${BASE}/blog/${esc(p.slug)}/</guid><pubDate>${new Date(p.date+'T12:00:00Z').toUTCString()}</pubDate><description>${esc(p.description)}</description></item>`).join('\n');
  await fs.writeFile(path.join(ROOT,'blog','feed.xml'),`<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Macca Blog</title><link>${BASE}/blog/</link><description>Independent Grand Theft Auto coverage</description>${items}</channel></rss>\n`);
  const rootMap=path.join(ROOT,'sitemap.xml');
  let rootXml;
  try { rootXml=await fs.readFile(rootMap,'utf8'); } catch { rootXml=`<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</sitemapindex>\n`; }
  if(/<urlset\b/i.test(rootXml)) rootXml=`<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <sitemap><loc>${BASE}/blog/sitemap.xml</loc></sitemap>\n</sitemapindex>\n`;
  else {
    const entries=[...rootXml.matchAll(/<sitemap>\s*<loc>([^<]+)<\/loc>\s*<\/sitemap>/gi)].map(m=>m[1]).filter(loc=>loc.startsWith(BASE+'/') && !loc.endsWith('/blog/sitemap.xml'));
    const locs=[...new Set([...entries,`${BASE}/blog/sitemap.xml`])];
    rootXml=`<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${locs.map(loc=>`  <sitemap><loc>${esc(loc)}</loc></sitemap>`).join('\n')}\n</sitemapindex>\n`;
  }
  await fs.writeFile(rootMap,rootXml);
}

function sourceLinks(posts,history) {
  return new Set([...posts.map(p=>p.sourceUrl),...history.flatMap(h=>[h.sourceUrl,...(h.sourceUrls||[])])].filter(Boolean));
}

function isNovel(item,posts,history,used=sourceLinks(posts,history)) {
  return !used.has(item.link) && !posts.some(p=>similarity(p.title,item.title)>0.36);
}

async function monitor() {
  successfulFeedReads=0;
  const candidates=await research({days:2});
  if(!successfulFeedReads) throw new Error('All research feeds failed; monitor cannot confirm whether there is new coverage.');
  const posts=await readJson(DATA_FILE,[]), history=await readJson(HISTORY_FILE,[]);
  const state=await readJson(MONITOR_STATE_FILE,{cooldowns:{}}), cooldowns=state.cooldowns||{};
  const now=Date.now(), retryAfter=6*60*60*1000;
  const fresh=candidates.filter(item=>{
    if(!isNovel(item,posts,history)) return false;
    const last=Date.parse(typeof cooldowns[item.link]==='string'?cooldowns[item.link]:cooldowns[item.link]?.attemptedAt||'');
    return !Number.isFinite(last)||now-last>=retryAfter;
  }).sort((a,b)=>topicScore(b)-topicScore(a));
  const candidate=fresh[0]||null;
  await fs.mkdir(path.dirname(CANDIDATE_FILE),{recursive:true});
  await writeJson(CANDIDATE_FILE,{candidate,detectedAt:new Date().toISOString()});
  if(process.env.GITHUB_OUTPUT) await fs.appendFile(process.env.GITHUB_OUTPUT,`should_generate=${candidate?'true':'false'}\n`);
  console.log(candidate?`Found novel GTA/Rockstar item: ${candidate.title} (${candidate.source})`:`No new GTA/Rockstar item in the last 48 hours; no AI call needed.`);
}

async function recordMonitorFailure() {
  const saved=await readJson(CANDIDATE_FILE,null), candidate=saved?.candidate;
  if(!candidate?.link) throw new Error('No monitored candidate was saved for retry cooldown.');
  const state=await readJson(MONITOR_STATE_FILE,{cooldowns:{}}), cooldowns=state.cooldowns||{};
  const cutoff=Date.now()-30*24*60*60*1000;
  for(const [link,value] of Object.entries(cooldowns)) {
    const attemptedAt=Date.parse(typeof value==='string'?value:value?.attemptedAt||'');
    if(!Number.isFinite(attemptedAt)||attemptedAt<cutoff) delete cooldowns[link];
  }
  cooldowns[candidate.link]={attemptedAt:new Date().toISOString(),title:candidate.title};
  await writeJson(MONITOR_STATE_FILE,{cooldowns});
  console.log(`Stored a six-hour AI retry cooldown for ${candidate.title}.`);
}

async function generate() {
  generate.rejected ||= 0;
  const dryRun=process.argv.includes('--dry-run');
  const candidates=await research();
  if(!candidates.length) { console.log('No recent GTA coverage found in configured news feeds; skipping this run.'); return; }
  const posts=await readJson(DATA_FILE,[]), history=await readJson(HISTORY_FILE,[]);
  const used=sourceLinks(posts,history), saved=await readJson(CANDIDATE_FILE,null), forced=saved?.candidate?.link?saved.candidate:null;
  const ranked=candidates.filter(c=>isNovel(c,posts,history,used)).sort((a,b)=>topicScore(b)-topicScore(a));
  const candidate=forced?(candidates.find(c=>c.link===forced.link)||forced):ranked[0];
  if(!candidate) { console.log('No sufficiently novel topic; skipping this run.'); return; }
  if(!isNovel(candidate,posts,history,used)) { console.log(`Monitored item is no longer novel; skipping: ${candidate.title}`); return; }
  if(dryRun) console.log(`Dry run selected candidate: ${candidate.title} (${candidate.link})`);
  const relatedFeeds=[candidate,...candidates.filter(c=>c.link!==candidate.link&&similarity(c.title,candidate.title)>0.2)].slice(0,5);
  const sourced=await Promise.all(relatedFeeds.map(fetchArticle));
  const mainSource=sourced.find(s=>s.link===candidate.link)||await fetchArticle(candidate);
  if(dryRun) console.log(`Research fetched ${sourced.length} source page(s); primary excerpt: ${(mainSource.excerpt||mainSource.description||'none').length} characters.`);
  const imageSources=sourced.filter(s=>s.imageUrl).map(s=>({url:s.imageUrl,sourceUrl:s.canonical||s.link,title:s.title}));
  const prompt=`Act as an editor validating the lead item before writing. It must be recent, materially about Grand Theft Auto or Rockstar Games, and contain a specific report or announcement. One credible publication report or one Rockstar/Take-Two primary source is enough; a second source is not required. Return JSON with skip:true and a brief reason for irrelevant items, duplicates, stale items, memes, vague posts, or unsupported speculation. Rumors and leaks may be covered when a credible publication reports them, with clear attribution and uncertainty. Treat third-party X posts as tips, not confirmation: prefer linked reporting or a Rockstar/Take-Two primary source in related coverage. Skip an isolated social post that offers no linked report or specific, verifiable information. Do not invent missing details. Describe crime and legal matters only as attributed allegations, never as established guilt; distinguish separate investigations and avoid naming a suspect unless the identity is essential and confirmed by authoritative sources. For accepted items, write a concise English post and attribute each claim to the named publisher, forum, or account. When details are sparse, write a short 150-250 word news brief that says what the source reported and what remains unknown. Cover Rockstar Games and Take-Two news as well as GTA. Return JSON only. For accepted items include title, description, category, tags (array), featured (boolean), sections (array of {heading,paragraphs:[...]}), thumbnail (string), thumbnailAlt (string), inlineImages (array of {url,alt,caption,sourceUrl}), and sources (array of {title,url,publisher}). Use 2-3 sections. Include the source URL as supplied. For thumbnail and inline images, choose only exact URLs from AVAILABLE SOURCE IMAGES. Never invent, alter, or guess an image URL. If none is suitable, set thumbnail to empty and inlineImages to []. Images are hotlinked from the reporting page and will not be copied into the repository. The article hero/banner is always the Macca image.
LEAD ITEM: ${candidate.title}
Publisher: ${candidate.source}
Date: ${candidate.date}
URL: ${candidate.link}
RSS summary: ${candidate.description}

AVAILABLE SOURCE IMAGES:
${JSON.stringify(imageSources)}

RELATED COVERAGE (use only if actually about the same story):
${sourced.map((s,i)=>`${i+1}. ${s.title}
URL: ${s.canonical||s.link}
Publisher: ${s.publisher}
Published: ${s.date}
Summary: ${s.description}
Article image: ${s.imageUrl||'[none]'}
Article excerpts: ${s.excerpt||'[No body available]'}`).join('\n\n')}
`;
  const generated=parseModel(await ask(prompt));
  if(dryRun) { if(generated.skip) { console.log(`Dry run provider declined topic: ${generated.reason||'no reason supplied'}`); return; } if(!generated.title||!Array.isArray(generated.sections)||generated.sections.length<2) throw new Error('Provider returned incomplete article JSON.'); console.log(`Dry run received valid article JSON (${generated.title}); no files changed.`); return; }
  if(generated.skip) {
    const reason=String(generated.reason||'AI validation found insufficient or unsuitable reporting.').slice(0,500);
    console.log(`AI validation skipped this item: ${reason}`);
    history.unshift({sourceUrl:candidate.link,title:candidate.title,date:new Date().toISOString(),status:'ai-rejected',reason,sourceUrls:relatedFeeds.map(s=>s.link)});
    await writeJson(HISTORY_FILE,history.slice(0,500));
    return;
  }
  if(!generated.title||!Array.isArray(generated.sections)||generated.sections.length<1) throw new Error('Provider returned incomplete article JSON.');
  const title=String(generated.title).trim();
  const allowedSourceUrls=new Set(sourced.flatMap(s=>[s.link,s.canonical]).concat(candidate.link).filter(Boolean));
  const cited=[...(Array.isArray(generated.sources)?generated.sources.filter(s=>allowedSourceUrls.has(s.url)):[]),{title:candidate.title,url:mainSource.canonical||candidate.link,publisher:candidate.source}];
  const allowedImageUrls=new Set(imageSources.map(s=>s.url));
  const inlineImages=(Array.isArray(generated.inlineImages)?generated.inlineImages:[]).filter(x=>allowedImageUrls.has(x.url)&&/^https:\/\//i.test(x.url||'')).slice(0,3).map(x=>({url:x.url,alt:String(x.alt||candidate.title).slice(0,180),caption:String(x.caption||'').slice(0,300),sourceUrl:allowedSourceUrls.has(x.sourceUrl)?x.sourceUrl:(imageSources.find(i=>i.url===x.url)?.sourceUrl||mainSource.canonical||candidate.link)}));
  const selectedThumbnail=allowedImageUrls.has(generated.thumbnail)?generated.thumbnail:(allowedImageUrls.has(mainSource.imageUrl)?mainSource.imageUrl:'');
  const p={...generated,title,description:String(generated.description||mainSource.description||candidate.description||title).slice(0,300),category:String(generated.category||'News'),tags:Array.isArray(generated.tags)?generated.tags.map(String).slice(0,10):['GTA'],thumbnail:selectedThumbnail,thumbnailAlt:String(generated.thumbnailAlt||title).slice(0,180),inlineImages,date:new Date().toISOString().slice(0,10),slug:slugify(title),sourceUrl:mainSource.canonical||candidate.link,sources:[...new Map(cited.filter(s=>s.url).map(s=>[s.url,s])).values()]};
  if(posts.some(x=>x.slug===p.slug||similarity(x.title,p.title)>0.36)) { console.log(`Skipping near-duplicate generated title: ${p.title}`); history.unshift({sourceUrl:candidate.link,title:candidate.title,date:new Date().toISOString(),status:'near-duplicate',sourceUrls:relatedFeeds.map(s=>s.link)}); await writeJson(HISTORY_FILE,history.slice(0,500)); generate.rejected++; if(generate.rejected<3) return generate(); console.log('Reached per-run limit while skipping duplicates.'); return; }
  posts.unshift(p); await writeJson(DATA_FILE,posts); history.unshift({slug:p.slug,title:p.title,sourceUrl:p.sourceUrl,sourceUrls:relatedFeeds.map(s=>s.link),date:p.date,status:'published',hash:crypto.createHash('sha256').update(`${p.title}|${p.sourceUrl}`).digest('hex')}); await writeJson(HISTORY_FILE,history.slice(0,500));
  if(process.env.INSTAGRAM_QUEUE_FILE) {
    const queue=await readJson(process.env.INSTAGRAM_QUEUE_FILE,[]);
    if(!queue.some(item=>item.slug===p.slug)) { queue.push({slug:p.slug}); await writeJson(process.env.INSTAGRAM_QUEUE_FILE,queue); }
  }
  if(process.env.YOUTUBE_QUEUE_FILE) {
    try {
      const queue=await readJson(process.env.YOUTUBE_QUEUE_FILE,[]);
      if(!queue.some(item=>item.slug===p.slug)) {
        queue.push({slug:p.slug,articleUrl:`${BASE}/blog/${encodeURIComponent(p.slug)}/`,sourceUrl:p.sourceUrl,title:p.title,description:p.description,sections:p.sections||[],tags:p.tags||[],thumbnail:p.thumbnail||'',thumbnailAlt:p.thumbnailAlt||'',inlineImages:p.inlineImages||[],sources:p.sources||[],queuedAt:new Date().toISOString()});
        await writeJson(process.env.YOUTUBE_QUEUE_FILE,queue);
        console.log(`Queued ${p.slug} for YouTube Shorts publication.`);
      }
    } catch(error) {
      console.error(`Could not add ${p.slug} to the YouTube queue; blog publication will continue: ${error.message}`);
    }
  }
  await build(); console.log(`Published ${p.slug}`);
}
function similarity(a,b){const words=x=>new Set(String(x).toLowerCase().split(/[^a-z0-9]+/).filter(w=>w.length>2));const x=words(a),y=words(b);if(!x.size||!y.size)return 0;return [...x].filter(v=>y.has(v)).length/new Set([...x,...y]).size;}
function topicScore(item){const t=`${item.title} ${item.description}`.toLowerCase();let score=0;if(/gta\s*6|grand theft auto vi|pre-?order|pre-?sale|price|leak|leaked|hack|hacked|breach|trailer|release date|rockstar/i.test(t))score+=5;if(/rumou?r|alleged|unconfirmed|speculation/i.test(t))score+=2;if(/mod|history|community|character|map|vehicle/i.test(t))score+=1;if(item.date)score+=Math.max(0,3-(Date.now()-Date.parse(item.date))/86400000/10);return score;}

const cmd=process.argv[2]||'build';
if(cmd==='build') await build();
else if(cmd==='monitor') await monitor();
else if(cmd==='record-monitor-failure') await recordMonitorFailure();
else if(cmd==='generate') {
  const count=Math.max(1,Math.min(BACKFILL?50:5,Number(process.argv.find(x=>x.startsWith('--count='))?.split('=')[1]||1)));
  for(let i=0;i<count;i++) { const before=(await readJson(DATA_FILE,[])).length; generate.rejected=0; await generate(); const after=(await readJson(DATA_FILE,[])).length; if(process.argv.includes('--dry-run')||after===before) break; }
}
else if(cmd==='discover') { const items=await research(); console.log(JSON.stringify(items.slice(0,BACKFILL?200:40),null,2)); }
else throw new Error(`Unknown command ${cmd}`);
