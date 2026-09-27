(() => {
  const feed = document.querySelector('[data-archive-feed]');
  if (!feed || !window.fetch || !window.DOMParser) return;
  const batch = feed.querySelector('[data-archive-batch]');
  const controls = feed.querySelector('[data-archive-controls]');
  const status = feed.querySelector('[data-archive-status]');
  let busy = false;
  let autoLoad = true;
  let observer;
  const seen = new Set([...batch.querySelectorAll('[data-archive-entry]')].map(el => el.dataset.archiveEntry));
  const load = async (manual = false) => {
    const next = controls.querySelector('[data-archive-next]');
    if (!next || busy) return;
    const url = new URL(next.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;
    busy = true;
    observer?.disconnect();
    feed.setAttribute('aria-busy', 'true');
    const button = controls.querySelector('[data-load-more]');
    if (button) button.disabled = true;
    status.textContent = feed.dataset.loading;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, { signal: controller.signal, credentials: 'same-origin' });
      if (!response.ok) throw new Error('Archive unavailable');
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const incoming = doc.querySelector('[data-archive-batch]');
      const nextControls = doc.querySelector('[data-archive-controls]');
      if (!incoming || !nextControls) throw new Error('Invalid archive response');
      const entries = [...incoming.querySelectorAll('[data-archive-entry]')].filter(el => !seen.has(el.dataset.archiveEntry));
      if (!entries.length) throw new Error('No new archive entries');
      entries.forEach(el => { seen.add(el.dataset.archiveEntry); batch.append(document.importNode(el, true)); });
      controls.replaceChildren(...[...nextControls.childNodes].map(el => document.importNode(el, true)));
      status.textContent = feed.dataset.loaded;
      if (manual) {
        const heading = batch.querySelector(`[data-archive-entry="${entries[0].dataset.archiveEntry}"] h2`);
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
      }
    } catch {
      // Never trap visitors in a failed infinite loader: standard links stay usable.
      autoLoad = false;
      status.textContent = feed.dataset.error;
    } finally {
      clearTimeout(timeout);
      busy = false;
      feed.removeAttribute('aria-busy');
      bind();
    }
  };
  const bind = () => {
    const button = controls.querySelector('[data-load-more]');
    if (!button) return;
    button.hidden = false;
    button.disabled = false;
    button.onclick = () => load(true);
    if (autoLoad && observer) observer.observe(button);
  };
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => {
      if (autoLoad && entries.some(entry => entry.isIntersecting)) load();
    }, { rootMargin: '0px 0px 350px 0px' });
  }
  document.querySelector('[data-guide-jump]')?.addEventListener('click', () => {
    autoLoad = false;
    observer?.disconnect();
  });
  bind();
})();
