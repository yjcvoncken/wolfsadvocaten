(() => {
  const labels = [...document.querySelectorAll('.team-list .team-meta h3, .team-list .team-email')];
  function fitLabel(label) {
    label.style.removeProperty('font-size');
    const available = label.clientWidth;
    if (!available) return;
    const range = document.createRange();
    range.selectNodeContents(label);
    const width = range.getBoundingClientRect().width;
    if (width > available) {
      const size = parseFloat(getComputedStyle(label).fontSize);
      label.style.fontSize = `${Math.floor(size * available / width * 100) / 100}px`;
    }
  }
  const fitLabels = () => labels.forEach(fitLabel);
  fitLabels();
  document.fonts.ready.then(fitLabels);
  if ('ResizeObserver' in window) {
    const observer = new ResizeObserver(fitLabels);
    new Set(labels.map(label => label.parentElement)).forEach(parent => observer.observe(parent));
  } else {
    window.addEventListener('resize', fitLabels);
  }
})();
