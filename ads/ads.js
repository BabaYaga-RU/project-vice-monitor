function detectAdBlock() {
  const probe = document.createElement('div');
  probe.className = 'adsbox ad-banner ad-unit adsbygoogle';
  probe.setAttribute('aria-hidden', 'true');
  probe.style.cssText = 'position:absolute!important;left:-10000px!important;top:-10000px!important;width:12px!important;height:12px!important;';
  document.body.append(probe);
  const blockedByStyle = probe.offsetHeight === 0 || getComputedStyle(probe).display === 'none';
  probe.remove();

  const scriptProbe = document.createElement('script');
  scriptProbe.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js';
  scriptProbe.async = true;
  let settled = false;
  const timer = window.setTimeout(() => {
    if (!settled) showAdBlockNotice();
  }, 2200);
  scriptProbe.onload = () => { settled = true; window.clearTimeout(timer); };
  scriptProbe.onerror = () => { settled = true; window.clearTimeout(timer); showAdBlockNotice(); };
  document.head.append(scriptProbe);
  if (blockedByStyle) showAdBlockNotice();
}

function showAdBlockNotice() {
  if (document.querySelector('.adblock-notice')) return;
  const notice = document.createElement('aside');
  notice.className = 'adblock-notice';
  notice.setAttribute('role', 'status');
  notice.innerHTML = '<div><strong>Ajude a manter o blog no ar</strong><p>Percebemos que um bloqueador de an&atilde;ncios pode estar ativo. Se puder, desative-o para este site e atualize a p&aacute;gina. As propagandas ajudam a cobrir os custos e a manter o blog dispon&iacute;vel, para publicarmos novidades o mais r&aacute;pido poss&iacute;vel.</p></div><button type="button" aria-label="Fechar aviso">&times;</button>';
  notice.querySelector('button').addEventListener('click', () => notice.remove());
  document.body.append(notice);
}
const AFFILIATE_SESSION_KEY = 'macca:affiliate-session:v1';

function affiliateSessionState() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(AFFILIATE_SESSION_KEY) || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveAffiliateSessionState(state) {
  try { sessionStorage.setItem(AFFILIATE_SESSION_KEY, JSON.stringify(state)); } catch { /* optional */ }
}

function affiliateKey(ad) {
  return String(ad.theme || ad.headline || ad.label || ad.href || 'ad').slice(0, 120);
}

function recordAffiliateEvent(ad, kind) {
  const state = affiliateSessionState();
  const key = affiliateKey(ad);
  const current = state[key] || {impressions:0, clicks:0};
  if (kind === 'impression') current.impressions += 1;
  if (kind === 'click') current.clicks += 1;
  state[key] = current;
  saveAffiliateSessionState(state);
}

function affiliateSessionLift(ad) {
  const current = affiliateSessionState()[affiliateKey(ad)];
  if (!current || current.impressions < 3) return 0;
  // Small, bounded per-session reinforcement. Context remains the main signal.
  const smoothedCtr = (current.clicks + 0.5) / (current.impressions + 5);
  return Math.max(-0.35, Math.min(1.25, (smoothedCtr - 0.08) * 5));
}

function observeAffiliateImpression(slot, link, ad) {
  if (!('IntersectionObserver' in window)) return;
  if (slot._maccaAdObserver) slot._maccaAdObserver.disconnect();
  if (slot._maccaAdImpressionTimer) window.clearTimeout(slot._maccaAdImpressionTimer);
  const observer = new IntersectionObserver(entries => {
    const visible = entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= 0.5);
    if (!visible || link.dataset.impressionRecorded === '1') return;
    slot._maccaAdImpressionTimer = window.setTimeout(() => {
      if (!document.contains(link) || link.dataset.impressionRecorded === '1') return;
      link.dataset.impressionRecorded = '1';
      recordAffiliateEvent(ad, 'impression');
    }, 1000);
  }, {threshold:[0.5]});
  observer.observe(link);
  slot._maccaAdObserver = observer;
}

function mountPklavcPopup() {
  const acceptedKey = 'macca:pklavc-blog-accepted';
  const dismissedKey = 'macca:pklavc-blog-dismissed-at';
  let accepted = false;
  let dismissedRecently = false;
  try {
    accepted = localStorage.getItem(acceptedKey) === '1';
    const dismissedAt = Number(localStorage.getItem(dismissedKey) || 0);
    dismissedRecently = dismissedAt > 0 && Date.now() - dismissedAt < 24 * 60 * 60 * 1000;
    if (dismissedAt && !dismissedRecently) localStorage.removeItem(dismissedKey);
  } catch {
    // Keep the popup usable when browser storage is unavailable.
  }
  if (accepted || dismissedRecently) return;

  let shown = false;
  const showAtScrollDepth = () => {
    if (shown) return;
    const scrollable = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    if (window.scrollY / scrollable < 0.35) return;
    shown = true;

    const backdrop = document.createElement('div');
    backdrop.className = 'pklavc-promo-backdrop';
    backdrop.innerHTML = `<section class="pklavc-promo" role="dialog" aria-modal="true" aria-labelledby="pklavc-promo-title" aria-describedby="pklavc-promo-description"><button class="pklavc-promo-close" type="button" aria-label="Close advertisement">&times;</button><div class="pklavc-promo-copy"><p class="eyebrow">FROM OUR PARTNER</p><h2 id="pklavc-promo-title">Curious minds, meet PKLAVC.</h2><p id="pklavc-promo-description">Explore the PKLAVC Blog for technology, engineering, open-source projects, and more.</p><a class="pklavc-promo-link" href="https://pklavc.com/blog" target="_blank" rel="sponsored noopener noreferrer">Visit the PKLAVC Blog <span aria-hidden="true">&#8599;</span></a></div><div class="pklavc-promo-art"><img src="/ads/partner.webp" alt="PKLAVC partner artwork" loading="lazy"></div></section>`;
    document.body.append(backdrop);

    const closeButton = backdrop.querySelector('.pklavc-promo-close');
    const close = wasDismissed => {
      if (wasDismissed) {
        try { localStorage.setItem(dismissedKey, String(Date.now())); } catch { /* storage is optional */ }
      }
      backdrop.remove();
      document.removeEventListener('keydown', onKeydown);
    };
    const onKeydown = event => {
      if (event.key === 'Escape') close(true);
    };
    closeButton.addEventListener('click', () => close(true));
    backdrop.querySelector('.pklavc-promo-link').addEventListener('click', () => {
      try { localStorage.setItem(acceptedKey, '1'); } catch { /* storage is optional */ }
      close(false);
    });
    document.addEventListener('keydown', onKeydown);
    closeButton.focus();
  };

  window.addEventListener('scroll', showAtScrollDepth, {passive: true});
}

async function mountAds() {
  mountPklavcPopup();
  try {
    const response = await fetch('/ads/config.json', {cache: 'no-store'});
    if (!response.ok) return;
    const config = await response.json();
    const placements = [...document.querySelectorAll('[data-ad-slot]')]
      .map(slot => {
        const name = slot.dataset.adSlot;
        const source = name.startsWith('sidebar-pklavc')
          ? config.slots?.['sidebar-pklavc']
          : name.startsWith('sidebar-affiliate')
            ? config.slots?.['sidebar-affiliate']
            : name.startsWith('sticky-affiliate')
              ? config.slots?.['sticky-affiliate']
            : config.slots?.[name];
        return {slot, ads: (source || []).filter(ad => ad.enabled && ad.href && ad.image)};
      })
      .filter(placement => placement.ads.length);
    if (!placements.length) return;

    const render = (slot, ad) => {
        const link = document.createElement('a');
        link.href = ad.href;
        link.target = '_blank';
        link.rel = 'sponsored noopener noreferrer';
        link.className = 'ad-creative';
        if (ad.theme && /^[a-z0-9-]+$/.test(ad.theme)) {
          link.classList.add(`ad-theme-${ad.theme}`);
        }

        const copy = document.createElement('span');
        copy.className = 'ad-copy';
        const kicker = document.createElement('span');
        kicker.className = 'ad-kicker';
        kicker.textContent = ad.kicker || 'MACCA BLOG PRESENTS';
        const headline = document.createElement('strong');
        headline.textContent = ad.headline || ad.label || 'Advertisement';
        const description = document.createElement('span');
        description.className = 'ad-description';
        description.textContent = ad.description || ad.alt || 'Visit pklavc.com';
        copy.append(kicker, headline, description);

        const art = document.createElement('span');
        art.className = 'ad-art';
        const image = document.createElement('img');
        image.src = ad.image;
        image.alt = ad.alt || 'Macca partner artwork';
        image.loading = 'lazy';
        art.append(image);
        link.append(copy, art);
        link.addEventListener('click', () => recordAffiliateEvent(ad, 'click'), {once:true});
        slot.replaceChildren(link);
        observeAffiliateImpression(slot, link, ad);
    };

    const stickyPlacements = placements.filter(({slot}) => slot.dataset.adSlot.startsWith('sticky-affiliate'));
    const regularPlacements = placements.filter(({slot}) => !slot.dataset.adSlot.startsWith('sticky-affiliate'));
    const contextText = String(document.body.dataset.adContext || '').toLowerCase();

    const affinity = ad => {
      const theme = String(ad.theme || '').toLowerCase();
      const headline = String(ad.headline || ad.label || '').toLowerCase();
      let score = Math.random() * 0.35;
      const gaming = /gta|rockstar|gaming|gameplay|console|ps5|xbox|pc|vehicle|map|graphics|performance/.test(contextText);
      const security = /hack|breach|security|privacy|leak|cyber|shinyhunters/.test(contextText);
      const shopping = /collector|edition|merch|preorder|pre-order|price|product|case|accessor/.test(contextText);
      const mobile = /mobile|phone|android|ios|handheld/.test(contextText);
      if (gaming && /redmagic|nubia|geekbuying|govee|sunsky/.test(theme + ' ' + headline)) score += 4;
      if (security && /hidemyname|turbovpn|vpn/.test(theme + ' ' + headline)) score += 5;
      if (shopping && /aliexpress|alibaba|gshopper|sunsky|icases|geekbuying/.test(theme + ' ' + headline)) score += 4;
      if (mobile && /redmagic|nubia|icases|sunsky/.test(theme + ' ' + headline)) score += 3;
      if (!gaming && !security && !shopping && !mobile) {
        if (/redmagic|geekbuying|aliexpress|gshopper/.test(theme + ' ' + headline)) score += 1;
      }
      score += affiliateSessionLift(ad);
      return score;
    };

    const rankedAds = ads => [...ads].sort((a, b) => affinity(b) - affinity(a));
    const contextualAd = (ads, excluded = new Set()) => {
      const available = ads.filter(ad => !excluded.has(ad.href));
      const pool = rankedAds(available.length ? available : ads).slice(0, Math.min(4, ads.length));
      return pool[Math.floor(Math.random() * Math.max(1, pool.length))] || ads[0];
    };
    const scheduleRotation = advance => {
      window.setTimeout(() => {
        advance();
        window.setInterval(advance, 6500 + Math.random() * 2500);
      }, 500 + Math.random() * 6500);
    };

    for (const {slot, ads} of regularPlacements) {
      let current = contextualAd(ads);
      let index = ads.indexOf(current);
      render(slot, current);
      if (ads.length > 1) {
        const advance = () => {
          const candidates = ads.filter((_, candidateIndex) => candidateIndex !== index);
          const nextAd = contextualAd(candidates);
          index = ads.indexOf(nextAd);
          render(slot, nextAd);
        };
        scheduleRotation(advance);
      }
    }

    const occupied = new Set();
    for (const placement of stickyPlacements) {
      const uniqueAds = placement.ads.filter(ad => !occupied.has(ad.href));
      placement.currentAd = contextualAd(uniqueAds.length ? uniqueAds : placement.ads);
      occupied.add(placement.currentAd.href);
      render(placement.slot, placement.currentAd);
    }
    for (const placement of stickyPlacements) {
      if (placement.ads.length < 2) continue;
      const advance = () => {
        const usedByOtherBanners = new Set(stickyPlacements
          .filter(other => other !== placement && other.currentAd)
          .map(other => other.currentAd.href));
        let available = placement.ads.filter(ad => !usedByOtherBanners.has(ad.href));
        const alternatives = available.filter(ad => ad.href !== placement.currentAd.href);
        if (alternatives.length) available = alternatives;
        if (!available.length) return;
        placement.currentAd = contextualAd(available, usedByOtherBanners);
        render(placement.slot, placement.currentAd);
      };
      scheduleRotation(advance);
    }
    if (document.querySelector('.sticky-ad-dock')) document.body.classList.add('has-sticky-ads');
  } catch (error) {
    console.warn('Ad configuration unavailable', error);
  }
}

document.addEventListener('DOMContentLoaded', mountAds);
