// 跨陣營價差頁：勾選「只看轉賣有賺的」時藏起淨利不到 0 的列（.cf-loss），並顯示目前列出幾項。
// 沒有 JavaScript 時篩選列保持隱藏，表格照常完整顯示。
(() => {
  const box = document.querySelector('[data-cf-filter]');
  const rows = [...document.querySelectorAll('#cf-table tbody tr')];
  if (!box || !rows.length) return;
  const input = box.querySelector('[data-cf-profit]');
  const count = box.querySelector('[data-cf-count]');
  const update = () => {
    let shown = 0;
    for (const row of rows) {
      row.hidden = input.checked && row.classList.contains('cf-loss');
      if (!row.hidden) shown += 1;
    }
    count.textContent = `列出 ${shown}／${rows.length} 項`;
  };
  input.addEventListener('change', update);
  box.hidden = false;
  update();
})();
