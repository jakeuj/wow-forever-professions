// Personal market page: renders market/data.json (built by scripts/build-market-data.py
// from the owner's Auctionator scan) as a searchable, sortable price list.
(() => {
  const PAGE = 120;
  const QUALITY = ['粗糙', '普通', '優秀', '精良', '史詩', '傳說', '神器', '傳家寶'];
  const ICON = 'https://wow.zamimg.com/images/wow/icons/medium/';
  const $ = selector => document.querySelector(selector);
  const form = $('[data-market-form]');
  const list = $('[data-market-list]');
  const summary = $('[data-market-summary]');
  const more = $('[data-market-more]');
  if (!form || !list) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  document.body.append(toast);
  let toastTimer;
  const notify = message => {
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('visible'), 3200);
  };

  const shortDay = iso => iso ? `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}` : '';
  const money = copper => {
    if (copper == null) return '—';
    const g = Math.floor(copper / 10000), s = Math.floor(copper / 100) % 100, c = copper % 100;
    const parts = [];
    if (g) parts.push([g.toLocaleString('zh-TW'), '金', 'g']);
    if (s) parts.push([s, '銀', 's']);
    if (c && g < 100) parts.push([c, '銅', 'c']);
    if (!parts.length) parts.push([0, '銅', 'c']);
    return parts;
  };

  let items = [];
  let latestDay = '';
  let classes = {};
  let subclasses = {};
  let shown = 0;
  let filtered = [];

  const readHash = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    for (const field of ['q', 'cat', 'quality', 'sort']) {
      if (params.has(field) && form.elements[field]) form.elements[field].value = params.get(field);
    }
    form.elements.latest.checked = params.get('latest') === '1';
  };
  const writeHash = () => {
    const params = new URLSearchParams();
    for (const field of ['q', 'cat', 'quality', 'sort']) {
      const value = form.elements[field].value;
      if (value && !(field === 'sort' && value === 'quality')) params.set(field, value);
    }
    if (form.elements.latest.checked) params.set('latest', '1');
    const hash = params.toString();
    history.replaceState(null, '', hash ? `#${hash}` : location.pathname + location.search);
  };

  const change = item => (item.prev && item.price != null) ? (item.price - item.prev) / item.prev : null;
  const sorters = {
    quality: (a, b) => (b.quality ?? -1) - (a.quality ?? -1) || (b.price ?? 0) - (a.price ?? 0),
    'price-desc': (a, b) => (b.price ?? 0) - (a.price ?? 0),
    'price-asc': (a, b) => (a.price ?? Infinity) - (b.price ?? Infinity),
    drop: (a, b) => (change(a) ?? Infinity) - (change(b) ?? Infinity),
    count: (a, b) => (b.count ?? 0) - (a.count ?? 0),
    name: (a, b) => a.name.localeCompare(b.name, 'zh-Hant-TW'),
  };

  const apply = () => {
    const q = form.elements.q.value.trim();
    const cat = form.elements.cat.value;
    const quality = form.elements.quality.value;
    const latestOnly = form.elements.latest.checked;
    filtered = items.filter(item => {
      if (q && !item.name.includes(q) && String(item.id) !== q) return false;
      if (cat.startsWith('c') && String(item.class) !== cat.slice(1)) return false;
      if (cat.startsWith('s') && `${item.class}.${item.subclass}` !== cat.slice(1)) return false;
      if (quality !== '' && String(item.quality) !== quality) return false;
      if (latestOnly && item.day !== latestDay) return false;
      return true;
    });
    filtered.sort(sorters[form.elements.sort.value] || sorters.quality);
    list.replaceChildren();
    shown = 0;
    renderMore();
    writeHash();
  };

  const renderRow = item => {
    const li = document.createElement('li');
    li.className = 'mk-row';
    if (item.day !== latestDay) li.classList.add('is-stale');

    const iconLink = document.createElement('a');
    iconLink.className = 'mk-icon';
    iconLink.href = `https://www.wowhead.com/forever/tw/item=${item.id}`;
    iconLink.target = '_blank';
    iconLink.rel = 'noopener noreferrer';
    iconLink.setAttribute('aria-label', `${item.name}：在 Wowhead 查看`);
    if (item.icon) {
      const img = document.createElement('img');
      img.src = `${ICON}${item.icon}.jpg`;
      img.alt = '';
      img.width = 36;
      img.height = 36;
      img.loading = 'lazy';
      img.decoding = 'async';
      iconLink.append(img);
    }

    const main = document.createElement('div');
    main.className = 'mk-main';
    const name = document.createElement('button');
    name.type = 'button';
    name.className = `mk-name q${item.quality ?? 1}`;
    name.textContent = item.name;
    name.title = `複製「${item.name}」`;
    name.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(item.name);
        notify(`已複製「${item.name}」，到拍賣場搜尋欄貼上`);
      } catch {
        notify(`無法自動複製，請手動選取「${item.name}」`);
      }
    });
    const meta = document.createElement('p');
    meta.className = 'mk-meta';
    const labels = [classes[item.class], subclasses[`${item.class}.${item.subclass}`]].filter((v, i, all) => v && all.indexOf(v) === i);
    if (item.level) labels.push(`${item.level} 級`);
    meta.append(labels.join('・'));
    const amobi = document.createElement('a');
    amobi.href = `https://wowamobi.com/items/${item.id}`;
    amobi.target = '_blank';
    amobi.rel = 'noopener noreferrer';
    amobi.textContent = '阿莫比';
    amobi.setAttribute('aria-label', `${item.name}：在阿莫比看三間拍賣場行情`);
    meta.append(labels.length ? '・' : '', amobi);
    main.append(name, meta);

    const price = document.createElement('div');
    price.className = 'mk-price';
    const value = document.createElement('strong');
    for (const [amount, unit, cls] of money(item.price)) {
      const span = document.createElement('span');
      span.className = `mk-coin mk-${cls}`;
      span.append(String(amount), document.createElement('small'));
      span.lastChild.textContent = unit;
      value.append(span);
    }
    const detail = document.createElement('span');
    detail.className = 'mk-detail';
    const parts = [];
    if (item.count != null) parts.push(`${item.count} 個`);
    parts.push(item.day === latestDay ? shortDay(item.day) : `${shortDay(item.day)} 看到`);
    detail.append(parts.join('・'));
    const delta = change(item);
    if (delta != null && Math.abs(delta) >= 0.005) {
      const tag = document.createElement('span');
      tag.className = delta < 0 ? 'mk-down' : 'mk-up';
      tag.textContent = ` 比 ${shortDay(item.prevDay)} ${delta < 0 ? '▼' : '▲'}${Math.round(Math.abs(delta) * 100)}%`;
      detail.append(tag);
    }
    price.append(value, detail);

    li.append(iconLink, main, price);
    return li;
  };

  const renderMore = () => {
    const slice = filtered.slice(shown, shown + PAGE);
    const fragment = document.createDocumentFragment();
    slice.forEach(item => fragment.append(renderRow(item)));
    list.append(fragment);
    shown += slice.length;
    const rest = filtered.length - shown;
    more.hidden = rest <= 0;
    more.textContent = `顯示更多（還有 ${rest.toLocaleString('zh-TW')} 件）`;
    summary.textContent = filtered.length
      ? `共 ${filtered.length.toLocaleString('zh-TW')} 件，顯示 ${shown.toLocaleString('zh-TW')} 件`
      : '沒有符合的物品；可以換個名稱，或把類型、品質改回「全部」。';
  };

  const fillCategories = () => {
    const select = form.elements.cat;
    const byClass = {};
    for (const key of Object.keys(subclasses)) (byClass[key.split('.')[0]] ||= []).push(key);
    for (const [classId, label] of Object.entries(classes)) {
      const group = document.createElement('optgroup');
      group.label = label;
      group.append(new Option(`${label}（全部）`, `c${classId}`));
      for (const key of byClass[classId] || []) {
        if (subclasses[key] && subclasses[key] !== label) group.append(new Option(`${label}・${subclasses[key]}`, `s${key}`));
      }
      select.append(group);
    }
  };

  let timer;
  form.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(apply, 150); });
  form.addEventListener('submit', event => { event.preventDefault(); apply(); });
  more.addEventListener('click', renderMore);

  fetch('./data.json', { cache: 'no-cache' })
    .then(response => {
      if (!response.ok) throw new Error(response.status);
      return response.json();
    })
    .then(data => {
      latestDay = data.latestDay;
      classes = data.classes;
      subclasses = data.subclasses;
      items = data.items.map(row => Object.fromEntries(data.fields.map((field, i) => [field, row[i]])));
      $('[data-market-scan]').textContent = `完整掃描 ${data.latestDay.replaceAll('-', '.')}`;
      $('[data-market-total]').textContent = `${items.length.toLocaleString('zh-TW')} 件物品`;
      $('[data-market-generated]').textContent = `掃描 / ${data.latestDay.replaceAll('-', '.')}・客戶端 ${data.build}`;
      fillCategories();
      readHash();
      form.hidden = false;
      apply();
    })
    .catch(() => {
      summary.textContent = '行情資料讀取失敗，請重新整理頁面。';
    });
})();
