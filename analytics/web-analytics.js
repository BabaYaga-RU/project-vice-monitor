(() => {
  if (document.querySelector('script[data-cf-beacon]')) return;
  fetch('/analytics/web-analytics.json', {cache:'no-store'})
    .then(response => response.ok ? response.json() : null)
    .then(config => {
      const token = typeof config?.token === 'string' ? config.token.trim() : '';
      if (!/^[a-f0-9]{16,64}$/i.test(token)) return;
      const script = document.createElement('script');
      script.defer = true;
      script.src = 'https://static.cloudflareinsights.com/beacon.min.js';
      script.setAttribute('data-cf-beacon', JSON.stringify({token}));
      document.head.append(script);
    })
    .catch(() => {});
})();
