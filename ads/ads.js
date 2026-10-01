async function mountAds() {
  try {
    const response = await fetch('/ads/config.json', {cache: 'no-store'});
    if (!response.ok) return;
    const config = await response.json();
    const placements = [...document.querySelectorAll('[data-ad-slot]')]
      .map(slot => ({slot, ads: (config.slots?.[slot.dataset.adSlot] || []).filter(ad => ad.enabled && ad.href && ad.image)}))
      .filter(placement => placement.ads.length);
    if (!placements.length) return;

    let index = 0;
    const render = () => {
      for (const {slot, ads} of placements) {
        const ad = ads[index % ads.length];
        const link = document.createElement('a');
        link.href = ad.href;
        link.target = '_blank';
        link.rel = 'sponsored noopener';
        link.className = 'ad-creative';

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
      }
    };

    render();
    if (placements.some(({ads}) => ads.length > 1)) {
      window.setInterval(() => { index += 1; render(); }, 7000);
    }
  } catch (error) {
    console.warn('Ad configuration unavailable', error);
  }
}

document.addEventListener('DOMContentLoaded', mountAds);
