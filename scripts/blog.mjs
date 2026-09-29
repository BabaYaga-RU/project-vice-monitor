#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
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
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const slugify = s => s.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,80) || 'gta-story';
const strip = s => s.replace(/<[^>]*>/g,' ').replace(/&amp;/g,'&').replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/\s+/g,' ').trim();

async function readJson(file, fallback) { try { return JSON.parse(await fs.readFile(file,'utf8')); } catch { return fallback; } }
async function writeJson(file, data) { await fs.mkdir(path.dirname(file),{recursive:true}); await fs.writeFile(file, JSON.stringify(data,null,2)+'\n'); }

async function research() {
  const items=[];
  for (const url of FEEDS) {
    try {
      const res=await fetch(url,{headers:{'user-agent':'GTA-Blog-Research/1.0'},signal:AbortSignal.timeout(12000)});
      if(!res.ok) continue;
      const xml=await res.text();
      for(const m of xml.matchAll(/<(item|entry)\b[\s\S]*?<\/\1>/gi)) {
        const block=m[0];
        const get=tag=>strip(block.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`,'i'))?.[1]?.replace(/<!\[CDATA\[|\]\]>/g,'' )||'');
        const title=get('title');
        let link=get('link') || block.match(/<link[^>]+href=["']([^"']+)/i)?.[1] || '';
        const description=get('description') || get('summary') || get('content');
        const date=get('pubDate') || get('published') || get('updated');
        const publisher=strip(block.match(/<source[^>]*>([\s\S]*?)<\/source>/i)?.[1]?.replace(/<!\[CDATA\[|\]\]>/g,'')||'') || new URL(url).hostname;
        if(title && /^https?:/.test(link)) items.push({title:title.replace(/\s+-\s+[^-]+$/,''),link,description,date,source:publisher});
      }
    } catch(e) { console.warn(`Research source unavailable: ${url}: ${e.message}`); }
  }
  // Discover reporting across independent gaming newsrooms, blogs and publications.
  const cutoff=Date.now()-1000*60*60*24*(BACKFILL?21:7);
  return items.filter(x=>/grand theft auto|\bgta\b|rockstar games|take[- ]two/i.test(`${x.title} ${x.description}`) && (!x.date || (Date.parse(x.date)>=cutoff && Date.parse(x.date)<=Date.now()+86400000)));
}

async function fetchArticle(item) {
  try {
    const response=await fetch(item.link,{headers:{'user-agent':'Mozilla/5.0 (compatible; MaccaBlogResearch/1.0)'},redirect:'follow',signal:AbortSignal.timeout(15000)});
    if(!response.ok) return item;
    const html=await response.text();
    const meta=(name)=>html.match(new RegExp(`<meta[^>]+(?:name|property)=["']${name}["'][^>]+content=["']([^"']+)`, 'i'))?.[1] || html.match(new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]+(?:name|property)=["']${name}["']`, 'i'))?.[1] || '';
    const title=strip(html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]||'') || item.title;
    const description=strip(meta('og:description')||meta('description')||item.description);
    const paragraphs=[...html.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map(m=>strip(m[1])).filter(t=>t.length>80).slice(0,9);
    return {...item,title,description,excerpt:paragraphs.join('\n\n').slice(0,6500),publisher:item.source||new URL(response.url).hostname,canonical:response.url};
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

function coverSvg(p) {
  const seed=crypto.createHash('sha256').update(p.slug).digest();
  const hue=92+(seed[0]%48), hue2=(hue+105+(seed[1]%35))%360;
  const title=String(p.title||'GTA Field Notes').replace(/[^\x20-\x7E]/g,' ').replace(/\s+/g,' ').trim();
  const words=title.split(' '); let lines=[], line='';
  for(const word of words){const next=(line+' '+word).trim();if(next.length>23&&line){lines.push(line);line=word;}else line=next;}
  if(line)lines.push(line); lines=lines.slice(0,3);
  const bars=Array.from({length:7},(_,i)=>{const h=24+seed[(i+2)%seed.length]%100,x=56+i*158,w=52+(seed[(i+9)%seed.length]%38);return `<rect x="${x}" y="${590-h}" width="${w}" height="${h}" rx="5" fill="#dff0d9" opacity="${0.08+(i%3)*0.03}"/>`;}).join('');
  const titleSvg=lines.map((v,i)=>`<text x="72" y="${338+i*62}" fill="#f5f5ed" font-family="Arial,sans-serif" font-size="${lines.length===1?52:43}" font-weight="700">${esc(v)}</text>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><defs><linearGradient id="g" x2="0" y2="1"><stop stop-color="#${((hue*3811+0x1a3026)%0xffffff).toString(16).padStart(6,'0')}"/><stop offset="1" stop-color="#101712"/></linearGradient><linearGradient id="a" x2="1" y2="1"><stop stop-color="hsl(${hue} 48% 48%)"/><stop offset="1" stop-color="hsl(${hue2} 45% 30%)"/></linearGradient></defs><rect width="1200" height="630" fill="url(#g)"/><circle cx="1010" cy="142" r="91" fill="url(#a)"/><path d="M0 500 190 355l92 87 173-220 102 174 160-132 89 104 176-180 218 187v255H0Z" fill="#09110d" opacity=".75"/>${bars}<text x="72" y="83" fill="#c5dc87" font-family="Arial,sans-serif" font-size="21" font-weight="700" letter-spacing="7">MACCA BLOG · ${esc(p.category||'GTA FIELD NOTES').toUpperCase()}</text>${titleSvg}<path d="M72 535h1056" stroke="#91b543" stroke-width="2" opacity=".7"/><text x="72" y="578" fill="#b8c5bb" font-family="Arial,sans-serif" font-size="19" letter-spacing="3">INDEPENDENT REPORTING · ${esc(p.date||'')}</text></svg>`;
}

function articleHtml(p, all) {
  const url=`${BASE}/blog/${p.slug}/`, imagePath=p.image||'/blog/assets/gta-fallback.svg', image=new URL(imagePath,`${BASE}/`).href;
  const adFallback=(slot)=>{const ad=slot==='sidebar'?'/blog/assets/ads/software-engineering.svg':'/blog/assets/ads/open-source.svg';const alt=slot==='sidebar'?'Software engineering and technology at pklavc.com':'Open source projects and engineering at pklavc.com';return `<a class="ad-fallback" href="https://pklavc.com" target="_blank" rel="sponsored noopener"><img src="${ad}" alt="${alt}"></a>`;};
  const related=all.filter(x=>x.slug!==p.slug && (x.category===p.category || x.tags.some(t=>p.tags.includes(t)))).slice(0,4);
  const latest=all.filter(x=>x.slug!==p.slug).slice(0,5);
  const body=(p.sections||[]).map(s=>`<section><h2>${esc(s.heading)}</h2>${(s.paragraphs||[]).map(x=>`<p>${esc(x)}</p>`).join('')}</section>`).join('');
  const cards=(items)=>items.length?items.map(x=>`<a class="post-card" href="/blog/${encodeURIComponent(x.slug)}/"><small>${esc(x.category)} · ${esc(x.date)}</small><strong>${esc(x.title)}</strong><span>${esc(x.description)}</span></a>`).join(''):'<p>More stories coming soon.</p>';
  const schema={"@context":"https://schema.org","@type":"Article",headline:p.title,description:p.description,datePublished:p.date,dateModified:p.date,mainEntityOfPage:url,image,author:{"@type":"Organization",name:'Macca Blog'},publisher:{"@type":"Organization",name:'Macca Blog'}};
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(p.title)} | Macca Blog</title><meta name="description" content="${esc(p.description)}"><meta name="robots" content="index, follow, max-image-preview:large"><link rel="canonical" href="${url}"><meta property="og:type" content="article"><meta property="og:title" content="${esc(p.title)}"><meta property="og:description" content="${esc(p.description)}"><meta property="og:image" content="${esc(image)}"><meta property="og:url" content="${url}"><meta property="og:site_name" content="Macca Blog"><meta property="og:locale" content="en_US"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${esc(p.title)}"><meta name="twitter:description" content="${esc(p.description)}"><meta name="twitter:image" content="${esc(image)}"><link rel="alternate" type="application/rss+xml" title="Macca Blog RSS" href="${BASE}/blog/feed.xml"><link rel="stylesheet" href="/blog/assets/blog.css"><script type="application/ld+json">${JSON.stringify(schema).replace(/</g,'\\u003c')}</script><script defer src="/blog/assets/blog.js"></script></head><body><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav><a href="/blog/">Home</a><a href="/blog/">Blog</a></nav></header><main class="layout"><article><a class="back" href="/blog/">← All stories</a><p class="eyebrow">${esc(p.category)} · <time datetime="${esc(p.date)}">${esc(p.date)}</time></p><h1>${esc(p.title)}</h1><p class="dek">${esc(p.description)}</p><figure><img src="${esc(imagePath)}" alt="${esc(p.imageAlt||'Grand Theft Auto editorial artwork')}" onerror="this.src='/blog/assets/gta-fallback.svg'"></figure><div class="article-body">${body}<h2>Sources and notes</h2><p>Claims, reports, leaks and rumors are attributed to their original sources. Unconfirmed information is labeled clearly and should not be read as established fact.</p><ul>${(p.sources||[]).map(s=>`<li><a rel="noopener noreferrer" href="${esc(s.url)}">${esc(s.title)}</a> <span>(${esc(s.publisher||new URL(s.url).hostname)})</span></li>`).join('')}</ul></div><div class="ad-slot" data-ad-slot="article-inline" aria-label="Advertisement">${adFallback('article-inline')}</div></article><aside><section class="side-section"><h2>Latest posts</h2><div class="post-list">${cards(latest)}</div></section><div class="ad-slot" data-ad-slot="sidebar" aria-label="Advertisement">${adFallback('sidebar')}</div><section class="side-section"><h2>Related stories</h2><div class="post-list">${cards(related)}</div></section></aside></main><footer><a href="/blog/">Macca Blog</a><span>Independent Grand Theft Auto coverage.</span></footer></body></html>`;
}

async function build() {
  const posts=(await readJson(DATA_FILE,[])).sort((a,b)=>b.date.localeCompare(a.date));
  for(const p of posts) { p.image=`/blog/assets/covers/${p.slug}.svg`; p.imageAlt=`Editorial cover illustration for ${p.title}`; await fs.mkdir(path.join(ROOT,'blog',p.slug),{recursive:true}); await fs.mkdir(path.join(ROOT,'blog','assets','covers'),{recursive:true}); await fs.writeFile(path.join(ROOT,'blog','assets','covers',`${p.slug}.svg`),coverSvg(p)); await fs.writeFile(path.join(ROOT,'blog',p.slug,'index.html'),articleHtml(p,posts)); }
  await writeJson(DATA_FILE,posts);
  const card=p=>`<a class="feature" href="/blog/${encodeURIComponent(p.slug)}/"><img src="${esc(p.image||'/blog/assets/gta-fallback.svg')}" alt="${esc(p.imageAlt||`Editorial cover illustration for ${p.title}`)}"><small>${esc(p.category)} · ${esc(p.date)}</small><h2>${esc(p.title)}</h2><p>${esc(p.description)}</p></a>`;
  const cats=[...new Set(posts.map(p=>p.category))].sort();
  const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Macca Blog | GTA News, History and Analysis</title><meta name="description" content="News, reports, rumors and analysis about Grand Theft Auto, with sources linked and unconfirmed claims clearly labeled."><meta name="robots" content="index, follow, max-image-preview:large"><link rel="canonical" href="${BASE}/blog/"><meta property="og:type" content="website"><meta property="og:site_name" content="Macca Blog"><meta property="og:title" content="Macca Blog | GTA News, History and Analysis"><meta property="og:description" content="News, reports, rumors and analysis about Grand Theft Auto."><meta property="og:url" content="${BASE}/blog/"><meta property="og:image" content="${BASE}/images/site-card.svg"><meta property="og:locale" content="en_US"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Macca Blog"><meta name="twitter:description" content="Sourced reporting and analysis from across the GTA community."><meta name="twitter:image" content="${BASE}/images/site-card.svg"><link rel="alternate" type="application/rss+xml" title="Macca Blog RSS" href="${BASE}/blog/feed.xml"><link rel="stylesheet" href="/blog/assets/blog.css"><script type="application/ld+json">${JSON.stringify({'@context':'https://schema.org','@type':'Blog','name':'Macca Blog','url':`${BASE}/blog/`})}</script><script defer src="/blog/assets/blog.js"></script></head><body><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav><a href="/blog/">Home</a><a href="/blog/">Blog</a></nav></header><main class="home"><section class="intro"><p class="eyebrow">GRAND THEFT AUTO, REPORTED</p><h1>Stories behind the streets.</h1><p>News, reporting, rumors and analysis from across the GTA community. Every story links back to its sources.</p><div class="categories">${cats.map(c=>`<span>${esc(c)}</span>`).join('')}</div></section><div class="ad-slot" data-ad-slot="blog-top" aria-label="Advertisement"><a class="ad-fallback" href="https://pklavc.com" target="_blank" rel="sponsored noopener"><img src="/blog/assets/ads/open-source.svg" alt="Open source projects and engineering at pklavc.com"></a></div><section><h2>Latest stories</h2><div class="grid">${posts.length?posts.map(card).join(''):'<p>No stories published yet.</p>'}</div></section><section><h2>Featured</h2><div class="grid">${posts.filter(p=>p.featured).map(card).join('')||posts.slice(0,2).map(card).join('')}</div></section></main><footer><a href="/blog/">Home</a><span>Macca Blog · independent Grand Theft Auto coverage.</span></footer></body></html>`;
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

async function generate() {
  generate.rejected ||= 0;
  const dryRun=process.argv.includes('--dry-run');
  const candidates=await research();
  if(!candidates.length) { console.log('No recent GTA coverage found in configured news feeds; skipping this run.'); return; }
  const posts=await readJson(DATA_FILE,[]), history=await readJson(HISTORY_FILE,[]);
  const used=new Set([...posts.map(p=>p.sourceUrl),...history.flatMap(h=>[h.sourceUrl,...(h.sourceUrls||[])])].filter(Boolean));
  const ranked=candidates.filter(c=>!used.has(c.link) && !posts.some(p=>similarity(p.title,c.title)>0.36)).sort((a,b)=>topicScore(b)-topicScore(a));
  const candidate=ranked[0];
  if(!candidate) { console.log('No sufficiently novel topic; skipping this run.'); return; }
  if(dryRun) console.log(`Dry run selected candidate: ${candidate.title} (${candidate.link})`);
  const relatedFeeds=candidates.filter(c=>similarity(c.title,candidate.title)>0.2).slice(0,5);
  const sourced=await Promise.all(relatedFeeds.map(fetchArticle));
  const mainSource=sourced.find(s=>s.link===candidate.link)||await fetchArticle(candidate);
  if(dryRun) console.log(`Research fetched ${sourced.length} source page(s); primary excerpt: ${(mainSource.excerpt||mainSource.description||'none').length} characters.`);
  const prompt=`Write a concise English post for Macca Blog about the lead news item below. One credible news/blog/forum report is enough to warrant a post. Never reject a topic just because it has only one source or limited detail. Do not invent missing details: attribute each claim to the named publisher/forum and clearly label leaks, rumors and unverified allegations as reports, not established fact. When details are sparse, write a short 150-250 word news brief that says what the source reported and what remains unknown. Cover Rockstar Games and Take-Two news as well as GTA. Do not return skip. Return JSON only with title, description, category, tags (array), image (empty unless supplied), imageAlt, featured (boolean), sections (array of {heading,paragraphs:[...]}), sources (array of {title,url,publisher}). Use 2-3 sections. Include the source URL as supplied.\nLEAD ITEM: ${candidate.title}\nPublisher: ${candidate.source}\nDate: ${candidate.date}\nURL: ${candidate.link}\nRSS summary: ${candidate.description}\n\nRELATED COVERAGE (use only if actually about the same story):\n${sourced.map((s,i)=>`${i+1}. ${s.title}\nURL: ${s.canonical||s.link}\nPublisher: ${s.publisher}\nPublished: ${s.date}\nSummary: ${s.description}\nArticle excerpts: ${s.excerpt||'[No body available]'}`).join('\n\n')}\n`;
  const generated=parseModel(await ask(prompt));
  if(dryRun) { if(generated.skip) { console.log(`Dry run provider declined topic: ${generated.reason||'no reason supplied'}`); return; } if(!generated.title||!Array.isArray(generated.sections)||generated.sections.length<2) throw new Error('Provider returned incomplete article JSON.'); console.log(`Dry run received valid article JSON (${generated.title}); no files changed.`); return; }
  if(generated.skip) { console.log('Provider declined despite instruction; building a strictly attributed short brief from the discovered report.'); generated.title=candidate.title; generated.description=candidate.description||candidate.title; generated.category=/take[- ]two|rockstar/i.test(candidate.title)?'Rockstar & Take-Two':'GTA News'; generated.tags=['GTA',candidate.source]; generated.sections=[{heading:'What the source reported',paragraphs:[`${candidate.source} reported: “${candidate.title}.” ${candidate.description?`The feed summary states: ${candidate.description}`:'The feed listing provides no further detail at this time.'}`]},{heading:'Context and confirmation',paragraphs:[`This post records the report by ${candidate.source} and does not treat unverified claims as confirmed. Readers should follow the linked source for updates and additional context.`]}]; generated.sources=[{title:candidate.title,url:candidate.link,publisher:candidate.source}]; }
  if(!generated.title||!Array.isArray(generated.sections)||generated.sections.length<1) throw new Error('Provider returned incomplete article JSON.');
  const title=String(generated.title).trim();
  const allowedSourceUrls=new Set(sourced.flatMap(s=>[s.link,s.canonical]).concat(candidate.link).filter(Boolean));
  const cited=[...(Array.isArray(generated.sources)?generated.sources.filter(s=>allowedSourceUrls.has(s.url)):[]),{title:candidate.title,url:mainSource.canonical||candidate.link,publisher:candidate.source}];
  const p={...generated,title,description:String(generated.description||mainSource.description||candidate.description||title).slice(0,300),category:String(generated.category||'News'),tags:Array.isArray(generated.tags)?generated.tags.map(String).slice(0,10):['GTA'],date:new Date().toISOString().slice(0,10),slug:slugify(title),sourceUrl:mainSource.canonical||candidate.link,sources:[...new Map(cited.filter(s=>s.url).map(s=>[s.url,s])).values()]};
  if(posts.some(x=>x.slug===p.slug||similarity(x.title,p.title)>0.36)) { console.log(`Skipping near-duplicate generated title: ${p.title}`); history.unshift({sourceUrl:candidate.link,title:candidate.title,date:new Date().toISOString(),status:'near-duplicate',sourceUrls:relatedFeeds.map(s=>s.link)}); await writeJson(HISTORY_FILE,history.slice(0,500)); generate.rejected++; if(generate.rejected<3) return generate(); console.log('Reached per-run limit while skipping duplicates.'); return; }
  posts.unshift(p); await writeJson(DATA_FILE,posts); history.unshift({slug:p.slug,title:p.title,sourceUrl:p.sourceUrl,sourceUrls:relatedFeeds.map(s=>s.link),date:p.date,status:'published',hash:crypto.createHash('sha256').update(`${p.title}|${p.sourceUrl}`).digest('hex')}); await writeJson(HISTORY_FILE,history.slice(0,500));
  await build(); console.log(`Published ${p.slug}`);
}
function similarity(a,b){const words=x=>new Set(String(x).toLowerCase().split(/[^a-z0-9]+/).filter(w=>w.length>2));const x=words(a),y=words(b);if(!x.size||!y.size)return 0;return [...x].filter(v=>y.has(v)).length/new Set([...x,...y]).size;}
function topicScore(item){const t=`${item.title} ${item.description}`.toLowerCase();let score=0;if(/gta\s*6|grand theft auto vi|pre-?order|pre-?sale|price|leak|leaked|hack|hacked|breach|trailer|release date|rockstar/i.test(t))score+=5;if(/rumou?r|alleged|unconfirmed|speculation/i.test(t))score+=2;if(/mod|history|community|character|map|vehicle/i.test(t))score+=1;if(item.date)score+=Math.max(0,3-(Date.now()-Date.parse(item.date))/86400000/10);return score;}

const cmd=process.argv[2]||'build';
if(cmd==='build') await build();
else if(cmd==='generate') {
  const count=Math.max(1,Math.min(BACKFILL?50:5,Number(process.argv.find(x=>x.startsWith('--count='))?.split('=')[1]||1)));
  for(let i=0;i<count;i++) { const before=(await readJson(DATA_FILE,[])).length; generate.rejected=0; await generate(); const after=(await readJson(DATA_FILE,[])).length; if(process.argv.includes('--dry-run')||after===before) break; }
}
else if(cmd==='discover') { const items=await research(); console.log(JSON.stringify(items.slice(0,BACKFILL?200:40),null,2)); }
else throw new Error(`Unknown command ${cmd}`);
