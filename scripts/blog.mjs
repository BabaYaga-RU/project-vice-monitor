#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = process.cwd();
const BASE = process.env.SITE_URL || 'https://macca-lab.onrender.com';
const FEEDS = [
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
        if(title && /^https?:/.test(link)) items.push({title,link,description,date,source:new URL(url).hostname});
      }
    } catch(e) { console.warn(`Research source unavailable: ${url}: ${e.message}`); }
  }
  // Discover reporting across independent gaming newsrooms, blogs and publications.
  const cutoff=Date.now()-1000*60*60*24*30;
  return items.filter(x=>/grand theft auto|\bgta\b|rockstar games/i.test(`${x.title} ${x.description}`) && (!x.date || (Date.parse(x.date)>=cutoff && Date.parse(x.date)<=Date.now()+86400000)));
}

async function ask(prompt) {
  const errors=[];
  const attempts=[];
  if(process.env.GEMINI_API_KEY) attempts.push(['Gemini',async()=>{
    const r=await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${process.env.GEMINI_API_KEY}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({contents:[{parts:[{text:prompt}]}],generationConfig:{responseMimeType:'application/json',temperature:0.4}})});
    if(!r.ok) throw new Error(`HTTP ${r.status}`); return (await r.json()).candidates?.[0]?.content?.parts?.[0]?.text;
  }]);
  if(process.env.CLOUDFLARE_API_TOKEN && process.env.CLOUDFLARE_ACCOUNT_ID) attempts.push(['Cloudflare Workers AI',async()=>{
    const url=`https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.1-8b-instruct`;
    const r=await fetch(url,{method:'POST',headers:{authorization:`Bearer ${process.env.CLOUDFLARE_API_TOKEN}`,'content-type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:prompt}]})});
    if(!r.ok) throw new Error(`HTTP ${r.status}`); return (await r.json()).result?.response;
  }]);
  if(process.env.OPENROUTER_API_KEY) attempts.push(['OpenRouter',async()=>{
    const r=await fetch('https://openrouter.ai/api/v1/chat/completions',{method:'POST',headers:{authorization:`Bearer ${process.env.OPENROUTER_API_KEY}`,'content-type':'application/json','HTTP-Referer':BASE,'X-Title':'GTA Research Blog'},body:JSON.stringify({model:'openrouter/auto',messages:[{role:'user',content:prompt}],response_format:{type:'json_object'}})});
    if(!r.ok) throw new Error(`HTTP ${r.status}`); return (await r.json()).choices?.[0]?.message?.content;
  }]);
  if(!attempts.length) throw new Error('No AI provider credentials configured.');
  for(const [name,call] of attempts) try { const out=await call(); if(out){console.log(`Article generated with ${name}`);return out;} throw new Error('Empty response'); } catch(e) { errors.push(`${name}: ${e.message}`); console.warn(`${name} unavailable; trying next provider.`); }
  throw new Error(`All AI providers failed: ${errors.join('; ')}`);
}

function parseModel(text) {
  const raw=String(text).replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');
  const a=raw.indexOf('{'), b=raw.lastIndexOf('}');
  if(a<0||b<a) throw new Error('Model did not return JSON.');
  return JSON.parse(raw.slice(a,b+1));
}

function articleHtml(p, all) {
  const url=`${BASE}/blog/${p.slug}/`, image=p.image||`${BASE}/blog/assets/gta-fallback.svg`;
  const adFallback=(slot)=>{const ad=slot==='sidebar'?'/blog/assets/ads/software-engineering.svg':'/blog/assets/ads/open-source.svg';const alt=slot==='sidebar'?'Software engineering and technology at pklavc.com':'Open source projects and engineering at pklavc.com';return `<a class="ad-fallback" href="https://pklavc.com" target="_blank" rel="sponsored noopener"><img src="${ad}" alt="${alt}"></a>`;};
  const related=all.filter(x=>x.slug!==p.slug && (x.category===p.category || x.tags.some(t=>p.tags.includes(t)))).slice(0,4);
  const latest=all.filter(x=>x.slug!==p.slug).slice(0,5);
  const body=(p.sections||[]).map(s=>`<section><h2>${esc(s.heading)}</h2>${(s.paragraphs||[]).map(x=>`<p>${esc(x)}</p>`).join('')}</section>`).join('');
  const cards=(items)=>items.length?items.map(x=>`<a class="post-card" href="/blog/${encodeURIComponent(x.slug)}/"><small>${esc(x.category)} · ${esc(x.date)}</small><strong>${esc(x.title)}</strong><span>${esc(x.description)}</span></a>`).join(''):'<p>More stories coming soon.</p>';
  const schema={"@context":"https://schema.org","@type":"Article",headline:p.title,description:p.description,datePublished:p.date,dateModified:p.date,mainEntityOfPage:url,image,author:{"@type":"Organization",name:'Macca Blog'},publisher:{"@type":"Organization",name:'Macca Blog'}};
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(p.title)} | Macca Blog</title><meta name="description" content="${esc(p.description)}"><link rel="canonical" href="${url}"><meta property="og:type" content="article"><meta property="og:title" content="${esc(p.title)}"><meta property="og:description" content="${esc(p.description)}"><meta property="og:image" content="${esc(image)}"><meta property="og:url" content="${url}"><meta property="og:site_name" content="Macca Blog"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${esc(p.title)}"><meta name="twitter:description" content="${esc(p.description)}"><meta name="twitter:image" content="${esc(image)}"><link rel="stylesheet" href="/blog/assets/blog.css"><script type="application/ld+json">${JSON.stringify(schema).replace(/</g,'\\u003c')}</script><script defer src="/blog/assets/blog.js"></script></head><body><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav><a href="/">Home</a><a href="/blog/">Blog</a></nav></header><main class="layout"><article><a class="back" href="/blog/">← All stories</a><p class="eyebrow">${esc(p.category)} · <time datetime="${esc(p.date)}">${esc(p.date)}</time></p><h1>${esc(p.title)}</h1><p class="dek">${esc(p.description)}</p><figure><img src="${esc(image)}" alt="${esc(p.imageAlt||'Grand Theft Auto editorial artwork')}" onerror="this.src='/blog/assets/gta-fallback.svg'"></figure><div class="article-body">${body}<h2>Sources and notes</h2><p>Claims, reports, leaks and rumors are attributed to their original sources. Unconfirmed information is labeled clearly and should not be read as established fact.</p><ul>${(p.sources||[]).map(s=>`<li><a rel="noopener noreferrer" href="${esc(s.url)}">${esc(s.title)}</a> <span>(${esc(s.publisher||new URL(s.url).hostname)})</span></li>`).join('')}</ul></div><div class="ad-slot" data-ad-slot="article-inline" aria-label="Advertisement">${adFallback('article-inline')}</div></article><aside><section class="side-section"><h2>Latest posts</h2><div class="post-list">${cards(latest)}</div></section><div class="ad-slot" data-ad-slot="sidebar" aria-label="Advertisement">${adFallback('sidebar')}</div><section class="side-section"><h2>Related stories</h2><div class="post-list">${cards(related)}</div></section></aside></main><footer><a href="/blog/">Macca Blog</a><span>Independent Grand Theft Auto coverage.</span></footer></body></html>`;
}

async function build() {
  const posts=(await readJson(DATA_FILE,[])).sort((a,b)=>b.date.localeCompare(a.date));
  for(const p of posts) { const dir=path.join(ROOT,'blog',p.slug); await fs.mkdir(dir,{recursive:true}); await fs.writeFile(path.join(dir,'index.html'),articleHtml(p,posts)); }
  const card=p=>`<a class="feature" href="/blog/${encodeURIComponent(p.slug)}/"><img src="${esc(p.image||'/blog/assets/gta-fallback.svg')}" alt=""><small>${esc(p.category)} · ${esc(p.date)}</small><h2>${esc(p.title)}</h2><p>${esc(p.description)}</p></a>`;
  const cats=[...new Set(posts.map(p=>p.category))].sort();
  const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Macca Blog | GTA News, History and Analysis</title><meta name="description" content="News, reports, rumors and analysis about Grand Theft Auto, with sources linked and unconfirmed claims clearly labeled."><link rel="canonical" href="${BASE}/blog/"><meta property="og:title" content="Macca Blog"><meta property="og:description" content="News, reports, rumors and analysis about Grand Theft Auto."><meta property="og:url" content="${BASE}/blog/"><meta property="og:image" content="${BASE}/blog/assets/gta-fallback.svg"><meta name="twitter:card" content="summary_large_image"><link rel="stylesheet" href="/blog/assets/blog.css"><script defer src="/blog/assets/blog.js"></script></head><body><header class="top"><a class="brand" href="/blog/">MACCA <b>BLOG</b></a><nav><a href="/">Home</a><a href="/blog/">Blog</a></nav></header><main class="home"><section class="intro"><p class="eyebrow">GRAND THEFT AUTO, REPORTED</p><h1>Stories behind the streets.</h1><p>News, reporting, rumors and analysis from across the GTA community. Every story links back to its sources.</p><div class="categories">${cats.map(c=>`<span>${esc(c)}</span>`).join('')}</div></section><div class="ad-slot" data-ad-slot="blog-top" aria-label="Advertisement"><a class="ad-fallback" href="https://pklavc.com" target="_blank" rel="sponsored noopener"><img src="/blog/assets/ads/open-source.svg" alt="Open source projects and engineering at pklavc.com"></a></div><section><h2>Latest stories</h2><div class="grid">${posts.length?posts.map(card).join(''):'<p>No stories published yet.</p>'}</div></section><section><h2>Featured</h2><div class="grid">${posts.filter(p=>p.featured).map(card).join('')||posts.slice(0,2).map(card).join('')}</div></section></main><footer><a href="/">Home</a><span>Macca Blog · independent Grand Theft Auto coverage.</span></footer></body></html>`;
  await fs.writeFile(path.join(ROOT,'blog','index.html'),html);
  const urls=posts.map(p=>`  <url><loc>${BASE}/blog/${esc(p.slug)}/</loc><lastmod>${esc(p.date)}</lastmod></url>`).join('\n');
  await fs.writeFile(path.join(ROOT,'blog','sitemap.xml'),`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>${BASE}/blog/</loc><lastmod>${new Date().toISOString().slice(0,10)}</lastmod></url>\n${urls}\n</urlset>\n`);
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
  const dryRun=process.argv.includes('--dry-run');
  const candidates=await research();
  if(!candidates.length) { console.log('No recent GTA coverage found in configured news feeds; skipping this run.'); return; }
  const posts=await readJson(DATA_FILE,[]), history=await readJson(HISTORY_FILE,[]);
  const used=new Set([...posts.map(p=>p.sourceUrl),...history.map(h=>h.sourceUrl)].filter(Boolean));
  const ranked=candidates.filter(c=>!used.has(c.link) && !posts.some(p=>similarity(p.title,c.title)>0.7)).sort((a,b)=>topicScore(b)-topicScore(a));
  const candidate=ranked[0];
  if(!candidate) { console.log('No sufficiently novel topic; skipping this run.'); return; }
  if(dryRun) console.log(`Dry run selected candidate: ${candidate.title} (${candidate.link})`);
  const sameTopic=candidates.filter(c=>similarity(c.title,candidate.title)>0.25).slice(0,5);
  const prompt=`Write an accurate English news article for Macca Blog using only the source material below. Never invent or upgrade a claim. Attribute each report, leak, rumor, alleged hack, preorder or price claim to its publisher. Label unverified claims as RUMOR, LEAK, or UNCONFIRMED in the headline or opening. Do not say Rockstar was hacked as fact unless at least two independent sources explicitly corroborate it; otherwise report that a named outlet alleges it and state that it is unverified. Include a source section listing every supplied URL used. If material is too thin, return {"skip":true,"reason":"insufficient sourced information"}. Return JSON only with title, description, category, tags (array), image (empty unless an image URL was supplied), imageAlt, featured (boolean), sections (array of {heading,paragraphs:[...]}), sources (array of {title,url,publisher}). Aim for 600-900 useful words without padding.\nMATCHING RECENT COVERAGE:\n${sameTopic.map((s,i)=>`${i+1}. ${s.title}\nURL: ${s.link}\nPublisher: ${s.source}\nDate: ${s.date}\nSummary: ${s.description}`).join('\n\n')}\n\nPRIMARY CANDIDATE: ${candidate.link}\n`;
  const generated=parseModel(await ask(prompt));
  if(dryRun) { if(!generated.skip && (!generated.title||!Array.isArray(generated.sections)||generated.sections.length<3)) throw new Error('Provider returned incomplete article JSON.'); console.log(`Dry run received valid article JSON (${String(generated.title||'untitled')}); no files changed.`); return; }
  if(generated.skip) { console.log(`Skipping weak source: ${generated.reason}`); return; }
  if(!generated.title||!Array.isArray(generated.sections)||generated.sections.length<3) throw new Error('Provider returned incomplete article JSON.');
  const title=String(generated.title).trim();
  const p={...generated,title,description:String(generated.description||candidate.description||title).slice(0,300),category:String(generated.category||'News'),tags:Array.isArray(generated.tags)?generated.tags.map(String).slice(0,10):['GTA'],date:new Date().toISOString().slice(0,10),slug:slugify(title),sourceUrl:candidate.link,sources:Array.isArray(generated.sources)&&generated.sources.length?generated.sources:sameTopic.map(s=>({title:s.title,url:s.link,publisher:s.source}))};
  if(posts.some(x=>x.slug===p.slug||similarity(x.title,p.title)>0.7)) throw new Error('Duplicate article detected after generation.');
  posts.unshift(p); await writeJson(DATA_FILE,posts); history.unshift({slug:p.slug,title:p.title,sourceUrl:p.sourceUrl,date:p.date,hash:crypto.createHash('sha256').update(`${p.title}|${p.sourceUrl}`).digest('hex')}); await writeJson(HISTORY_FILE,history.slice(0,500));
  await build(); console.log(`Published ${p.slug}`);
}
function similarity(a,b){const words=x=>new Set(String(x).toLowerCase().split(/[^a-z0-9]+/).filter(w=>w.length>2));const x=words(a),y=words(b);if(!x.size||!y.size)return 0;return [...x].filter(v=>y.has(v)).length/new Set([...x,...y]).size;}
function topicScore(item){const t=`${item.title} ${item.description}`.toLowerCase();let score=0;if(/gta\s*6|grand theft auto vi|pre-?order|pre-?sale|price|leak|leaked|hack|hacked|breach|trailer|release date|rockstar/i.test(t))score+=5;if(/rumou?r|alleged|unconfirmed|speculation/i.test(t))score+=2;if(/mod|history|community|character|map|vehicle/i.test(t))score+=1;if(item.date)score+=Math.max(0,3-(Date.now()-Date.parse(item.date))/86400000/10);return score;}

const cmd=process.argv[2]||'build';
if(cmd==='build') await build(); else if(cmd==='generate') await generate(); else throw new Error(`Unknown command ${cmd}`);
