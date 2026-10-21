(() => {
  const panel = document.querySelector('[data-live-panel]');
  if (!panel) return;
  const grid = panel.querySelector('.stats-live-grid');
  const status = panel.querySelector('[data-live-status]');
  let timer;
  let inFlight = false;
  function fill(name, rows) {
    const list = panel.querySelector(`[data-live-${name}]`);
    list.replaceChildren();
    if (!rows.length) {
      const item = document.createElement('li');
      item.textContent = 'No active visits in this group.';
      list.append(item);
    }
    for (const row of rows) {
      const item = document.createElement('li');
      const label = document.createElement('span');
      label.textContent = row.label;
      const count = document.createElement('strong');
      count.textContent = row.total;
      item.append(label, count);
      list.append(item);
    }
  }
  async function refresh() {
    if (!panel.open || document.hidden || inFlight) return;
    inFlight = true;
    try {
      const response = await fetch(panel.dataset.liveUrl, {credentials: 'same-origin', cache: 'no-store'});
      if (!response.ok) throw new Error('Live data is temporarily unavailable.');
      const data = await response.json();
      panel.querySelector('[data-live-total]').textContent = data.active;
      fill('pages', data.pages);
      fill('sources', data.sources);
      fill('countries', data.countries);
      grid.hidden = false;
      status.textContent = `Updated ${new Date(data.as_of).toLocaleTimeString()}. Active means seen within 2 minutes.`;
    } catch {
      status.textContent = 'Live data is temporarily unavailable. Please reopen this panel to retry.';
    } finally {
      inFlight = false;
    }
  }
  function sync() {
    clearInterval(timer);
    if (panel.open && !document.hidden) {
      refresh();
      timer = setInterval(refresh, 15000);
    }
  }
  panel.addEventListener('toggle', sync);
  document.addEventListener('visibilitychange', sync);
})();
