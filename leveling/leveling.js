// Leveling page: recompute material costs from the market page's data (../market/data.json,
// built from the owner's Auctionator scan). The HTML already holds a snapshot, so the page
// reads fine without JavaScript or when the data cannot be loaded.
// Rows: <tr data-lv-id="item id" data-lv-qty="n bought at auction" data-lv-price="snapshot copper"
// [data-lv-fixed="copper for NPC-bought units" data-lv-other="their count"]>; tables with
// data-lv-phase also carry data-lv-vendor (copper returned by selling the crafted items).
// Route variants: <nav data-lv-tabs> links to <div data-lv-variant id="…"> panels. Without
// JavaScript every panel stays visible in order. The hash picks the panel; an anchor inside a
// panel (old links such as #route or #materials) opens the panel that holds it.
(() => {
  const nav = document.querySelector('[data-lv-tabs]');
  const panels = [...document.querySelectorAll('[data-lv-variant]')];
  if (!nav || !panels.length) return;
  const tabs = [...nav.querySelectorAll('[data-lv-tab]')];
  const panelFor = hash => {
    const target = hash.length > 1 && document.getElementById(decodeURIComponent(hash.slice(1)));
    return (target && panels.find(p => p === target || p.contains(target))) || null;
  };
  const show = panel => {
    panels.forEach(p => { p.hidden = p !== panel; });
    tabs.forEach(t => {
      if (t.dataset.lvTab === panel.id) t.setAttribute('aria-current', 'true');
      else t.removeAttribute('aria-current');
    });
  };
  nav.classList.add('is-tabs');
  show(panelFor(location.hash) || panels[0]);
  window.addEventListener('hashchange', () => {
    const panel = panelFor(location.hash);
    if (!panel) return;
    show(panel);
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target && target !== panel) target.scrollIntoView();
  });
})();

(() => {
  const phases = document.querySelectorAll('[data-lv-phase]');
  if (!phases.length) return;

  const trim = text => text.replace(/\.0$/, '');
  const unit = c => (c >= 10000 ? `${(c / 10000).toFixed(2)}g` : `${trim((c / 100).toFixed(1))} 銀`);
  const total = c => (c >= 10000 ? `${(c / 10000).toFixed(1)}g` : unit(c));
  const setText = (root, selector, text) => root.querySelectorAll(selector).forEach(node => { node.textContent = text; });
  const shortTag = () => Object.assign(document.createElement('span'), { className: 'eg-tag skip', textContent: '不夠' });
  const dateChip = document.querySelector('[data-lv-date]');

  const apply = data => {
    const scanTime = data.snapshotAt || data.savedAt || data.scanStartedAt || data.latestDay;
    if (dateChip?.dataset.lvSnapshot && !(Date.parse(scanTime) > Date.parse(dateChip.dataset.lvSnapshot))) return;
    const f = data.fields;
    const [iId, iPrice, iCount] = ['id', 'price', 'count'].map(k => f.indexOf(k));
    const live = new Map(data.items.filter(r => r[iPrice] && r[iCount] !== 0)
      .map(r => [r[iId], { price: r[iPrice], count: r[iCount] }]));

    phases.forEach(table => {
      const body = table.querySelector('tbody');
      const rows = [...body.querySelectorAll('tr[data-lv-id]')].map(row => {
        const hit = live.get(Number(row.dataset.lvId));
        const qty = Number(row.dataset.lvQty);
        // data-lv-fixed: copper for the units bought from NPCs, which the scan does not price.
        const fixed = Number(row.dataset.lvFixed || 0);
        if (!qty) return { row, sub: fixed };
        const price = hit ? hit.price : Number(row.dataset.lvPrice);
        const cell = row.querySelector('[data-lv-unit]');
        cell.textContent = unit(Math.round((price * qty + fixed) / (qty + (fixed ? Number(row.dataset.lvOther || 0) : 0) || 1)));
        if (!hit) cell.append(Object.assign(document.createElement('span'), { className: 'lv-stale', textContent: '沿用快照' }));
        if (hit && hit.count != null) {
          setText(row, '[data-lv-listed]', hit.count.toLocaleString('en-US'));
          const tag = row.querySelector('[data-lv-short]');
          tag.replaceChildren(...(hit.count < qty ? [shortTag()] : []));
        }
        return { row, sub: price * qty + fixed };
      });
      const sum = rows.reduce((acc, r) => acc + r.sub, 0);
      rows.sort((a, b) => b.sub - a.sub).forEach(({ row, sub }) => {
        const share = sum ? (sub / sum) * 100 : 0;
        setText(row, '[data-lv-sub]', total(sub));
        setText(row, '[data-lv-pct]', `${Math.round(share)}%`);
        row.querySelector('.lv-share').style.setProperty('--share', `${share.toFixed(1)}%`);
        body.append(row);
      });
      const net = sum - Number(table.dataset.lvVendor || 0);
      setText(table, '[data-lv-total]', total(sum));
      setText(table, 'tfoot [data-lv-net]', total(net));
      const card = document.querySelector(`[data-lv-card="${table.dataset.lvPhase}"]`);
      if (card) {
        setText(card, '[data-lv-gross]', total(sum));
        setText(card, '[data-lv-net]', total(net));
      }
    });

    // Plan totals stay inside each route variant, so one route's plans never add to another's.
    const scopes = document.querySelectorAll('[data-lv-variant]');
    (scopes.length ? [...scopes] : [document]).forEach(scope => {
      const planSummary = scope.querySelector('[data-lv-plan-total]');
      let planTotal = Number(planSummary?.dataset.lvPlanFixed || 0);
      scope.querySelectorAll('.lv-plans tr[data-lv-id]').forEach(row => {
        const hit = live.get(Number(row.dataset.lvId));
        setText(row, '[data-lv-unit]', hit ? unit(hit.price) : '部落沒貨');
        setText(row, '[data-lv-listed]', hit ? `${hit.count ?? '?'} 件` : '—');
        if (hit && row.hasAttribute('data-lv-buy')) planTotal += hit.price;
      });
      if (planSummary && planTotal) planSummary.textContent = total(planTotal);
    });

    const stamp = data.scanStartedAt || data.savedAt;
    if (dateChip && stamp) {
      dateChip.textContent = `${data.scanStartedAt ? '完整掃描' : '部落掃描'} ${stamp.slice(0, 16).replace('T', ' ').replace(/-/g, '.')}`;
    }
  };

  fetch('../market/data.json', { cache: 'no-cache' })
    .then(response => {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    })
    .then(apply)
    .catch(() => {
      if (dateChip) dateChip.textContent += '（讀不到最新行情，顯示快照）';
    });
})();
