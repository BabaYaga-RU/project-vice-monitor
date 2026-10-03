import fs from 'node:fs/promises';
import path from 'node:path';

export const HUBS = [
  {
    slug:'gta-6',
    title:'GTA 6',
    description:'Source-backed GTA 6 coverage, updates, analysis and explainers from Macca Blog.',
    test:post=>/gta\s*(?:6|vi)|grand theft auto\s*(?:6|vi)/i.test(textOf(post)),
  },
  {
    slug:'gta-6/release-date',
    title:'GTA 6 Release Date',
    description:'Latest sourced coverage about the GTA 6 release date, delays, launch timing and availability.',
    test:post=>isGta6(post)&&/release|launch|date|delay|november|may|pre-?order/i.test(textOf(post)),
  },
  {
    slug:'gta-6/characters',
    title:'GTA 6 Characters',
    description:'Coverage about GTA 6 characters, actors and story details, with sources attached to each report.',
    test:post=>isGta6(post)&&/character|lucia|jason|actor|cast|story|protagonist/i.test(textOf(post)),
  },
  {
    slug:'gta-6/map',
    title:'GTA 6 Map',
    description:'GTA 6 map reporting, locations, scale, Vice City, weather and world details collected from sourced stories.',
    test:post=>isGta6(post)&&/map|vice city|location|world|weather|hurricane|storm|key west|scale/i.test(textOf(post)),
  },
  {
    slug:'gta-6/trailers',
    title:'GTA 6 Trailers',
    description:'GTA 6 trailer coverage, official footage, screenshots and marketing updates.',
    test:post=>isGta6(post)&&/trailer|footage|screenshot|marketing|video|teaser/i.test(textOf(post)),
  },
  {
    slug:'gta-6/editions',
    title:'GTA 6 Editions & Collectibles',
    description:'GTA 6 editions, pre-orders, collector items, merchandise and pricing coverage.',
    test:post=>isGta6(post)&&/edition|collector|collectable|collectible|merch|pre-?order|price|case/i.test(textOf(post)),
  },
  {
    slug:'gta-6/online',
    title:'GTA 6 Online',
    description:'Reports and analysis about GTA 6 multiplayer and the future of GTA Online.',
    test:post=>isGta6(post)&&/online|multiplayer|lobb|player/i.test(textOf(post)),
  },
  {
    slug:'gta-online',
    title:'GTA Online',
    description:'GTA Online updates, events and ongoing Rockstar support coverage.',
    test:post=>/gta\s*online/i.test(textOf(post)),
  },
  {
    slug:'rockstar-games',
    title:'Rockstar Games',
    description:'Rockstar Games news, studio updates, legal stories, releases and official announcements.',
    test:post=>/rockstar|take[- ]two/i.test(textOf(post)),
  },
];

function textOf(post){
  return `${post?.title||''} ${post?.description||''} ${post?.category||''} ${(post?.tags||[]).join(' ')}`;
}
function isGta6(post){
  return /gta\s*(?:6|vi)|grand theft auto\s*(?:6|vi)/i.test(textOf(post));
}
function esc(value){
  return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function absolute(base,value){
  try{return new URL(value,base.endsWith('/')?base:`${base}/`).href;}catch{return `${base}/images/macca-blog-banner.jpg`;}
}
function card(post){
  const image=post.discoverImage||post.socialImage||post.thumbnail||'/images/macca-blog-banner.webp';
  return `<article class="growth-card"><a href="/blog/${encodeURIComponent(post.slug)}/"><img src="${esc(image)}" alt="${esc(post.thumbnailAlt||post.title)}" loading="lazy" decoding="async"><span><small>${esc(post.category||'Macca Blog')} · ${esc(post.date||'')}</small><strong>${esc(post.title)}</strong><p>${esc(post.description||'')}</p></span></a></article>`;
}

export function relatedHubs(post){
  return HUBS.filter(hub=>hub.test(post)).slice(0,4);
}

export function socialScore(post){
  const text=textOf(post).toLowerCase();
  const hook=String(post.socialHook||post.instagramCaptionLead||post.description||'').trim();
  let score=18;
  if(/gta\s*(?:6|vi)|grand theft auto\s*(?:6|vi)/i.test(text)) score+=18;
  if(/rockstar|take[- ]two/i.test(text)) score+=10;
  if(/trailer|release|launch|map|weather|hurricane|online|collector|edition|pre-?order|official|confirmed|announc/i.test(text)) score+=16;
  if(/lawsuit|hack|breach|mod|physics|vehicle|character|actor|merch/i.test(text)) score+=8;
  if(/rumou?r|alleged|unconfirmed|speculation|reddit/i.test(text)) score-=12;
  if(post.featured) score+=8;
  if(hook.length>=45&&hook.length<=220) score+=10;
  if(post.thumbnail||post.socialImage||post.discoverImage) score+=6;
  const sourceText=(post.sources||[]).map(source=>`${source.publisher||''} ${source.title||''} ${source.url||''}`).join(' ').toLowerCase();
  if(/rockstar|take[- ]two|rockstargames\.com/.test(sourceText)) score+=12;
  return Math.max(0,Math.min(100,Math.round(score)));
}

export function searchConsoleBonus(item,feedback){
  const text=textOf(item).toLowerCase();
  let bonus=0;
  for(const signal of feedback?.topicSignals||[]){
    const term=String(signal.term||'').toLowerCase().trim();
    if(term.length<3||!text.includes(term)) continue;
    bonus+=Number(signal.weight)||0;
  }
  return Math.max(-2.5,Math.min(3,bonus));
}

export async function buildGrowthPages({root=process.cwd(),base='https://macca-lab.onrender.com',posts=[]}={}){
  const sorted=[...posts].filter(post=>post?.slug).sort((a,b)=>String(b.updatedAt||b.date||'').localeCompare(String(a.updatedAt||a.date||'')));
  const stylesheet='<link rel="stylesheet" href="/blog/assets/blog.css"><link rel="stylesheet" href="/blog/assets/growth.css"><link rel="stylesheet" href="/ads/ads.css"><script defer src="/ads/ads.js"></script><link rel="stylesheet" href="/skylet/widget.css?v=20260929.1">';
  const footer='<footer><div class="footer-about"><a href="/blog/">Macca Blog</a><span>Independent coverage, linked to its sources.</span></div><nav class="footer-links" aria-label="Footer navigation"><a href="/blog/">Blog</a><a href="/social/">Social</a><a href="/about/">About</a><a href="/privacy/">Privacy Policy</a></nav><p class="footer-disclaimer">Macca Lab is an independent project and is not affiliated with or endorsed by Rockstar Games or Take-Two Interactive.</p></footer>';

  for(const hub of HUBS){
    const matching=sorted.filter(hub.test);
    const dir=path.join(root,...hub.slug.split('/'));
    await fs.mkdir(dir,{recursive:true});
    const canonical=`${base}/${hub.slug}/`;
    const lastModified=matching[0]?.updatedAt||matching[0]?.date||'';
    const facts=matching.slice(0,6).map(post=>`<li><a href="/blog/${encodeURIComponent(post.slug)}/">${esc(post.title)}</a><span>${esc(post.description||'')}</span></li>`).join('');
    const relatedNav=HUBS.filter(other=>other.slug!==hub.slug&&matching.some(other.test)).slice(0,6).map(other=>`<a href="/${other.slug}/">${esc(other.title)}</a>`).join('');
    const schema={"@context":"https://schema.org","@type":"CollectionPage","name":hub.title,"description":hub.description,"url":canonical,"isPartOf":{"@type":"WebSite","name":"Macca Lab","url":`${base}/`}};
    const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(hub.title)} | Macca Blog</title><meta name="description" content="${esc(hub.description)}"><meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1"><link rel="canonical" href="${canonical}"><meta property="og:type" content="website"><meta property="og:title" content="${esc(hub.title)}"><meta property="og:description" content="${esc(hub.description)}"><meta property="og:url" content="${canonical}"><meta property="og:image" content="${esc(absolute(base,matching[0]?.discoverImage||matching[0]?.socialImage||'/images/macca-blog-banner.jpg'))}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">${JSON.stringify(schema).replace(/</g,'\\u003c')}</script>${stylesheet}</head><body class="has-sticky-ads" data-ad-context="${esc(hub.title)}"><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav aria-label="Main navigation"><a href="/blog/">Blog</a><a href="/social/">Social</a></nav></header><main class="growth-page"><nav class="growth-breadcrumb"><a href="/blog/">Macca Blog</a><span>›</span><span>${esc(hub.title)}</span></nav><section class="growth-hero"><p class="eyebrow">EVERGREEN COVERAGE</p><h1>${esc(hub.title)}</h1><p>${esc(hub.description)}</p>${lastModified?`<small>Latest source-backed update: ${esc(String(lastModified).slice(0,10))}</small>`:''}</section>${facts?`<section class="growth-summary"><div class="section-heading"><span>WHAT WE KNOW</span><h2>Latest source-backed developments</h2></div><ul>${facts}</ul></section>`:''}<section><div class="section-heading"><span>READ MORE</span><h2>Latest ${esc(hub.title)} stories</h2></div><div class="growth-grid">${matching.slice(0,24).map(card).join('')||'<p>No matching stories yet.</p>'}</div></section>${relatedNav?`<nav class="growth-related" aria-label="Related topic hubs">${relatedNav}</nav>`:''}</main>${footer}<script defer src="/skylet/widget.js?v=20260929.1"></script></body></html>`;
    await fs.writeFile(path.join(dir,'index.html'),html);
  }

  let youtube=[];
  let instagram={};
  try{youtube=JSON.parse(await fs.readFile(path.join(root,'blog','youtube-published.json'),'utf8'));}catch{}
  try{instagram=JSON.parse(await fs.readFile(path.join(root,'blog','instagram-published.json'),'utf8'));}catch{}
  const youtubeBySlug=new Map((Array.isArray(youtube)?youtube:[]).map(item=>[item.slug,item]));
  const instagramBySlug=new Map(Object.entries(instagram||{}).map(([articleUrl,item])=>[articleUrl.split('/').filter(Boolean).pop(),item]));
  const socialDir=path.join(root,'social');
  await fs.mkdir(socialDir,{recursive:true});
  const socialPosts=sorted.slice(0,12);
  const featured=socialPosts[0];
  const socialCards=socialPosts.map(post=>{
    const yt=youtubeBySlug.get(post.slug);
    const ig=instagramBySlug.get(post.slug);
    return `<article class="social-story"><a class="social-story-main" data-social-story href="/blog/${encodeURIComponent(post.slug)}/"><img src="${esc(post.discoverImage||post.socialImage||post.thumbnail||'/images/macca-blog-banner.webp')}" alt="${esc(post.title)}"><span><small>${esc(post.category||'Macca Blog')} · ${esc(post.date||'')}</small><strong>${esc(post.title)}</strong><p>${esc(post.description||'')}</p></span></a><div class="social-story-links">${yt?.youtubeUrl?`<a href="${esc(yt.youtubeUrl)}" target="_blank" rel="noopener noreferrer">YouTube</a>`:''}${ig?.permalink?`<a href="${esc(ig.permalink)}" target="_blank" rel="noopener noreferrer">Instagram</a>`:''}</div></article>`;
  }).join('');
  const socialHtml=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Latest GTA & Rockstar Stories | Macca</title><meta name="description" content="The latest GTA and Rockstar stories from Macca Blog, plus Macca the Gator on YouTube and Instagram."><meta name="robots" content="index, follow, max-image-preview:large"><link rel="canonical" href="${base}/social/"><meta property="og:title" content="Macca — latest GTA & Rockstar stories"><meta property="og:description" content="Jump from Macca's social channels into the latest source-backed GTA and Rockstar coverage."><meta property="og:image" content="${esc(absolute(base,featured?.discoverImage||featured?.socialImage||'/images/macca-blog-banner.jpg'))}">${stylesheet}</head><body class="has-sticky-ads" data-ad-context="GTA Rockstar social"><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav><a href="/blog/">Blog</a><a href="/gta-6/">GTA 6</a></nav></header><main class="growth-page social-landing"><section class="growth-hero"><p class="eyebrow">FROM SOCIAL TO THE FULL STORY</p><h1>Latest from Macca</h1><p>Open the full sourced story, then keep reading related GTA and Rockstar coverage.</p></section><div class="social-story-list">${socialCards}</div></main>${footer}<script>const q=new URLSearchParams(location.search);const source=q.get('utm_source')||'social';for(const a of document.querySelectorAll('[data-social-story]')){const u=new URL(a.href,location.origin);u.searchParams.set('utm_source',source);u.searchParams.set('utm_medium','social');u.searchParams.set('utm_campaign','macca_social_hub');a.href=u.pathname+u.search;}</script><script defer src="/skylet/widget.js?v=20260929.1"></script></body></html>`;
  await fs.writeFile(path.join(socialDir,'index.html'),socialHtml);
}
