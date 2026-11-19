import { legacyPlannerUrl } from './legacy-links.mjs?v=20261119-guild';

const destination = legacyPlannerUrl(location.href);
if (destination) {
  location.replace(destination);
} else {
  window.addEventListener('hashchange', () => {
    const destination = legacyPlannerUrl(location.href);
    if (destination) location.replace(destination);
  });

  const status = document.getElementById('guild-copy-status');
  document.querySelectorAll('[data-copy-target]').forEach(button => {
    const target = document.getElementById(button.dataset.copyTarget);
    const label = button.querySelector('[data-copy-label]');
    const defaultLabel = label.textContent;
    let resetLabelTimer;

    button.hidden = false;
    button.addEventListener('click', async () => {
      const text = target.textContent.trim();
      status.textContent = '';
      try {
        await navigator.clipboard.writeText(text);
        clearTimeout(resetLabelTimer);
        label.textContent = '已複製';
        button.classList.add('is-copied');
        resetLabelTimer = setTimeout(() => {
          label.textContent = defaultLabel;
          button.classList.remove('is-copied');
        }, 2400);
        status.textContent = `已複製「${text}」`;
      } catch {
        status.textContent = '無法自動複製，請選取上方文字手動複製。';
      }
    });
  });
}
