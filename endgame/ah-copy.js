// Click an item name to copy the exact in-game name for the auction house search box.
// Markup: <span data-ah="配方：貓鼬藥劑">貓鼬藥劑</span>; without JavaScript it stays plain text.
(() => {
  const items = document.querySelectorAll('[data-ah]');
  if (!items.length) return;

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

  const selectText = node => {
    const range = document.createRange();
    range.selectNodeContents(node);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  };

  items.forEach(item => {
    const name = item.dataset.ah;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ah-copy';
    button.dataset.ah = name;
    button.title = `複製「${name}」`;
    button.setAttribute('aria-label', `${item.textContent.trim()}：複製「${name}」到拍賣場搜尋`);
    const label = document.createElement('span');
    label.className = 'ah-copy-label';
    label.append(...item.childNodes);
    const icon = document.createElement('span');
    icon.className = 'ah-copy-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '⧉';
    button.append(label, icon);
    item.replaceWith(button);

    let resetTimer;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(name);
        clearTimeout(resetTimer);
        button.classList.add('is-copied');
        resetTimer = setTimeout(() => button.classList.remove('is-copied'), 2000);
        notify(`已複製「${name}」，到拍賣場搜尋欄貼上`);
      } catch {
        const hidden = document.createElement('span');
        hidden.className = 'ah-copy-fallback';
        hidden.textContent = name;
        button.after(hidden);
        selectText(hidden);
        notify(`無法自動複製，已選取「${name}」，請按 Ctrl+C 或 ⌘C`);
        setTimeout(() => hidden.remove(), 8000);
      }
    });
  });

  document.querySelectorAll('[data-ah-hint]').forEach(hint => { hint.hidden = false; });
})();
