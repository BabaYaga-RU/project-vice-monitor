async function mountAds() {
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
