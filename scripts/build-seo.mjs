#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';

const ROOT=process.cwd();
const SITE=(process.env.SITE_URL||'https://macca-lab.onrender.com').replace(/\/$/,'');
const SKIP=new Set(['.git','node_modules','blog','scripts','.github','coverage','dist','build']);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const decode=s=>String(s||'').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;|&apos;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/Ã¡/g,'á').replace(/Ã©/g,'é').replace(/Ã­/g,'í').replace(/Ã³/g,'ó').replace(/Ãº/g,'ú').replace(/Ã£/g,'ã').replace(/Ãµ/g,'õ').replace(/Ã§/g,'ç').replace(/Ã‰/g,'É').replace(/Ã“/g,'Ó').replace(/Ã€/g,'À').replace(/Ã‚/g,'Â').replace(/Â(?=\s|[·…])/g,'');
const strip=s=>decode(String(s||'').replace(/<script\b[\s\S]*?<\/script>|<style\b[\s\S]*?<\/style>/gi,' ').replace(/<[^>]+>/g,' ')).replace(/\s+/g,' ').trim();
async function walk(dir=''){
  const out=[];
  for(const ent of await fs.readdir(path.join(ROOT,dir),{withFileTypes:true})){
    if(ent.name.startsWith('.')||SKIP.has(ent.name))continue;
    const rel=path.posix.join(dir.replaceAll('\\','/'),ent.name);
    if(ent.isDirectory())out.push(...await walk(rel));
    else if(ent.isFile()&&ent.name.toLowerCase()==='index.html')out.push(rel);
  }
  return out;
}
function attr(tag,key){return tag.match(new RegExp(`\\b${key}\\s*=\\s*(["'])(.*?)\\1`,'i'))?.[2]||'';}
function replaceTag(head,replacement,re){let done=false;const next=head.replace(re,()=>{if(done)return '';done=true;return replacement;});return done?next:`${next}\n${replacement}`;}
function titleOf(html,file){if(file==='index.html')return 'Macca Lab | Software Engineering, Study & Experiments';return strip(html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1])||strip(html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i)?.[1])||'Macca Lab';}
function descOf(html,title,file){if(file==='index.html')return 'Macca Lab is a practical software engineering laboratory with study materials, technical experiments, interactive tests, and learning projects.';const old=html.match(/<meta\b[^>]*name=["']description["'][^>]*>/i)?.[0];const desc=old?attr(old,'content'):'';if(desc.length>60)return desc;
  const h1=strip(html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i)?.[1]);
  const paras=[...html.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)].map(m=>strip(m[1])).filter(t=>t.length>45);
  const candidate=paras.find(x=>!/^study\s+play\s+macca/i.test(x))||h1||`${title} at Macca Lab.`;
  return candidate.length>165?candidate.slice(0,162).replace(/\s+\S*$/,'')+'…':candidate;
}
function pageSchema(url,title,description,file){
  const home=url===`${SITE}/`,routePath=new URL(url).pathname;
  const type=home?'WebSite':(/^\/(study|play)\/$/.test(routePath)?'CollectionPage':/(?:simulador|calculator|interactive-tool)\/$/i.test(routePath)?'SoftwareApplication':'WebPage');
  const data={'@context':'https://schema.org','@type':type,'@id':`${url}#${type.toLowerCase()}`,'url':url,'name':title,'description':description,'inLanguage':(/lang=["']pt/i.test(file.__html||'')?'pt-BR':'en')};
  if(home)data.publisher={'@type':'Organization','name':'Macca Lab','url':`${SITE}/`};
  if(type==='SoftwareApplication'){data.applicationCategory='EducationalApplication';data.operatingSystem='Web';}
  return data;
}
const files=await walk(); const urls=[];const directory=[];
for(const file of files){
  let html=await fs.readFile(path.join(ROOT,file),'utf8');
  if(!/<head\b/i.test(html)||!/<\/head>/i.test(html))continue;
  const rel=file==='index.html'?'':file.slice(0,-'index.html'.length);
  const url=new URL(rel,`${SITE}/`).href;
  const routePath=new URL(url).pathname;
  const internalToolRoute=/\/simulador\/(?:app|src)\/$/i.test(routePath);
  const title=titleOf(html,file);const description=descOf(html,title,file);const lang=html.match(/<html\b[^>]*\blang=["']([^"']+)/i)?.[1]||'en';
  const image=`${SITE}/images/site-card.svg`;
  let head=html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)[1];
  head=replaceTag(head,`<title>${esc(title)}</title>`,/<title\b[^>]*>[\s\S]*?<\/title>/i);
  head=replaceTag(head,`<meta name="description" content="${esc(description)}">`,/<meta\b(?=[^>]*\bname=["']description["'])[^>]*>/i);
  head=replaceTag(head,`<meta name="robots" content="${internalToolRoute?'noindex, follow':'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'}">`,/<meta\b(?=[^>]*\bname=["']robots["'])[^>]*>/i);
  head=replaceTag(head,`<link rel="canonical" href="${esc(url)}">`,/<link\b(?=[^>]*\brel=["']canonical["'])[^>]*>/i);
  const metas=[['og:type',url.endsWith('/blog/')?'website':'website'],['og:site_name','Macca Lab'],['og:title',title],['og:description',description],['og:url',url],['og:image',image],['og:image:alt',`Macca Lab — ${title}`],['og:locale',lang.toLowerCase().startsWith('pt')?'pt_BR':'en_US'],['twitter:card','summary_large_image'],['twitter:title',title],['twitter:description',description],['twitter:image',image]];
  for(const [key,value] of metas){const attribute=key.startsWith('twitter:')?'name':'property';head=replaceTag(head,`<meta ${attribute}="${key}" content="${esc(value)}">`,new RegExp(`<meta\\b(?=[^>]*\\b(?:property|name)=["']${key.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}["'])[^>]*>`,'i'));}
  head=replaceTag(head,`<link rel="alternate" type="application/rss+xml" title="Macca Blog RSS" href="${SITE}/blog/feed.xml">`,/<link\b(?=[^>]*\btype=["']application\/rss\+xml["'])[^>]*>/i);
  const schema=pageSchema(url,title,description,Object.assign(new String(file),{__html:html}));
  const ld=`<script type="application/ld+json">${JSON.stringify(schema).replace(/</g,'\\u003c')}</script>`;
  head=head.replace(/<script\b(?=[^>]*\btype=["']application\/ld\+json["'])[^>]*>[\s\S]*?<\/script>/gi,'');head+=`\n${ld}\n`;
  html=html.replace(/<head\b[^>]*>[\s\S]*?<\/head>/i,m=>m.replace(/>[\s\S]*<\/head>/,`>${head}</head>`));
  await fs.writeFile(path.join(ROOT,file),html);
  if(!internalToolRoute){urls.push(url);directory.push({url,title,description,lang});}
}
try{const posts=JSON.parse(await fs.readFile(path.join(ROOT,'blog','posts.json'),'utf8'));for(const p of posts)directory.push({url:`${SITE}/blog/${encodeURIComponent(p.slug)}/`,title:decode(p.title),description:decode(p.description),lang:'en'});}catch{}
const xmlEscape=s=>esc(s);
const pages=`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.sort().map(u=>`  <url><loc>${xmlEscape(u)}</loc></url>`).join('\n')}\n</urlset>\n`;
await fs.writeFile(path.join(ROOT,'sitemap-pages.xml'),pages);
await fs.writeFile(path.join(ROOT,'sitemap.xml'),`<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <sitemap><loc>${SITE}/sitemap-pages.xml</loc></sitemap>\n  <sitemap><loc>${SITE}/blog/sitemap.xml</loc></sitemap>\n</sitemapindex>\n`);
await fs.writeFile(path.join(ROOT,'robots.txt'),`User-agent: *\nAllow: /\n\nSitemap: ${SITE}/sitemap.xml\n`);
const primary=directory.filter(p=>p.url===`${SITE}/`||/\/(study|play)\/$/.test(p.url)||/laboratorio|simulador/i.test(p.url)).sort((a,b)=>a.url.localeCompare(b.url));
const entry=p=>`- [${p.title}](${p.url}): ${p.description}`;
await fs.writeFile(path.join(ROOT,'llms.txt'),`# Macca Lab\n\n> A practical software engineering lab for study materials, experiments, interactive tests, and technical projects. Macca Blog publishes sourced reporting about Grand Theft Auto, Rockstar Games, and Take-Two.\n\nThe main site is organized around learning resources and interactive experiments. Blog pages are editorial content and link to their sources.\n\n## Main pages\n\n${primary.map(entry).join('\n')}\n\n## Blog and feeds\n\n- [Macca Blog](${SITE}/blog/): Sourced reporting, rumors clearly labeled, and analysis.\n- [RSS feed](${SITE}/blog/feed.xml): Recent blog articles.\n\n## Discovery\n\n- [XML sitemap index](${SITE}/sitemap.xml)\n- [Page sitemap](${SITE}/sitemap-pages.xml)\n- [Blog sitemap](${SITE}/blog/sitemap.xml)\n`);
await fs.writeFile(path.join(ROOT,'llms-full.txt'),`# Macca Lab — Public Page Directory\n\n${directory.sort((a,b)=>a.url.localeCompare(b.url)).map(entry).join('\n')}\n`);
await fs.writeFile(path.join(ROOT,'ai.txt'),`# Public content discovery\n\nWebsite: ${SITE}/\nCrawl policy: ${SITE}/robots.txt\nSitemap: ${SITE}/sitemap.xml\nPage directory: ${SITE}/llms.txt\nFull directory: ${SITE}/llms-full.txt\n\nThese optional directories describe public pages. They do not control crawler access or guarantee indexing, ranking, training, or citations.\n`);
await fs.mkdir(path.join(ROOT,'images'),{recursive:true});
await fs.writeFile(path.join(ROOT,'images','site-card.svg'),`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#e6f1db"/><stop offset="1" stop-color="#9bc58b"/></linearGradient></defs><rect width="1200" height="630" fill="#14251c"/><circle cx="995" cy="160" r="110" fill="url(#g)"/><path d="M0 500 220 330l150 120 180-235 140 185 170-135 340 240v125H0Z" fill="#263c2f"/><text x="80" y="160" fill="#a8ce72" font-family="Arial,sans-serif" font-size="32" letter-spacing="8">MACCA</text><text x="80" y="300" fill="#f4f4ec" font-family="Arial,sans-serif" font-size="90" font-weight="700">Software Engineering Lab</text><text x="85" y="370" fill="#c4d0c5" font-family="Arial,sans-serif" font-size="32">Study · Experiments · Interactive tools</text></svg>\n`);
console.log(`SEO metadata, ${urls.length} canonical page URLs, sitemap index and AI directories generated.`);
