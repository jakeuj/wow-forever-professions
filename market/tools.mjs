export function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

export function table(headings, rows) {
  const box = element('div');
  box.className = 'tool-table';
  const grid = element('table');
  const head = grid.createTHead().insertRow();
  for (const label of headings) {
    const cell = element('th', label);
    cell.scope = 'col';
    head.append(cell);
  }
  const body = grid.createTBody();
  for (const cells of rows) {
    const row = body.insertRow();
    for (const cell of cells) row.insertCell().append(cell);
  }
  box.append(grid);
  return box;
}

export function link(text, url) {
  const anchor = element('a', text);
  anchor.href = url;
  anchor.className = 'text-link';
  return anchor;
}

export function readLocal(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}

export function saveLocal(key, data) {
  try { localStorage.setItem(key, JSON.stringify(data)); }
  catch { /* The form works for the current visit. */ }
}

export function shoppingText(title, rows) {
  const names = [...new Set(rows.map(row => row.name))].filter(name => name && !/[\^"\r\n]/u.test(name));
  return names.length ? [title, ...names.map(name => `"${name}"`)].join('^') : '';
}

export function copyButton(label, text) {
  const button = element('button', label);
  button.type = 'button';
  button.className = 'button-compact';
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(typeof text === 'function' ? text() : text);
      button.textContent = '已複製';
    } catch {
      const field = element('textarea');
      field.readOnly = true;
      field.value = typeof text === 'function' ? text() : text;
      button.replaceWith(field);
      field.select();
    }
  });
  return button;
}

export function shoppingButtons(title, rows) {
  const box = element('div');
  box.className = 'tool-actions';
  if (rows.length) {
    const text = shoppingText(title, rows);
    if (text) box.append(copyButton('複製拍賣小幫手清單', text));
    box.append(copyButton('複製含數量清單', rows.map(row => `${row.name} × ${row.quantity}`).join('\n')));
  }
  return box;
}

export function numericItems(text) {
  const items = new Map();
  for (const token of text.trim().split(/[\n,，]+/u).filter(Boolean)) {
    const pair = token.trim().match(/^(\d+)\s*[:：×x\s]\s*(\d+)$/u);
    if (!pair || !pair.slice(1).every(value => Number.isSafeInteger(Number(value)) && Number(value) > 0)) {
      throw new Error('每列填「物品 ID：數量」，例如 12359：20。');
    }
    const id = Number(pair[1]);
    const count = Number(pair[2]) + (items.get(id) || 0);
    if (!Number.isSafeInteger(count)) throw new Error('數量過大。');
    items.set(id, count);
  }
  return items;
}
