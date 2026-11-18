(() => {
  const scan = document.getElementById('cl-scan');
  const stale = document.getElementById('cl-stale');
  const checkAge = () => {
    stale.hidden = Date.now() - Date.parse(scan.dateTime) <= 48 * 60 * 60 * 1000;
  };
  const revealStage = () => {
    const stage = document.getElementById(location.hash.slice(1));
    if (stage instanceof HTMLDetailsElement) {
      stage.open = true;
      stage.scrollIntoView();
    }
  };

  checkAge();
  window.addEventListener('pageshow', checkAge);
  window.addEventListener('hashchange', revealStage);
  revealStage();
})();
