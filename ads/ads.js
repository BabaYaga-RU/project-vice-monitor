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
        slot.replaceChildren(link);
    };

    const stickyPlacements = placements.filter(({slot}) => slot.dataset.adSlot.startsWith('sticky-affiliate'));
    const regularPlacements = placements.filter(({slot}) => !slot.dataset.adSlot.startsWith('sticky-affiliate'));
    const randomAd = ads => ads[Math.floor(Math.random() * ads.length)];
    const scheduleRotation = advance => {
      window.setTimeout(() => {
        advance();
        window.setInterval(advance, 6500 + Math.random() * 2500);
      }, 500 + Math.random() * 6500);
    };

    for (const {slot, ads} of regularPlacements) {
      let index = Math.floor(Math.random() * ads.length);
      render(slot, ads[index]);
      if (ads.length > 1) {
        const advance = () => {
          let next = Math.floor(Math.random() * (ads.length - 1));
          if (next >= index) next += 1;
          index = next;
          render(slot, ads[index]);
        };
        scheduleRotation(advance);
      }
    }

    const occupied = new Set();
    for (const placement of stickyPlacements) {
      const uniqueAds = placement.ads.filter(ad => !occupied.has(ad.href));
      placement.currentAd = randomAd(uniqueAds.length ? uniqueAds : placement.ads);
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
        placement.currentAd = randomAd(available);
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
