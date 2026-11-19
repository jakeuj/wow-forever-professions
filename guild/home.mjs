import { legacyPlannerUrl } from './legacy-links.mjs?v=20261119-guild';

const destination = legacyPlannerUrl(location.href);
if (destination) {
  location.replace(destination);
} else {
  window.addEventListener('hashchange', () => {
    const destination = legacyPlannerUrl(location.href);
    if (destination) location.replace(destination);
  });

  const contactStatus = document.getElementById('guild-copy-status');
  document.querySelectorAll('[data-copy-target]').forEach(button => {
    const target = document.getElementById(button.dataset.copyTarget);
    const status = button.dataset.copyStatus
      ? document.getElementById(button.dataset.copyStatus)
      : contactStatus;
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
        status.textContent = status === contactStatus ? `已複製「${text}」` : '已複製。';
      } catch {
        status.textContent = '無法自動複製，請選取上方文字手動複製。';
      }
    });
  });
}
