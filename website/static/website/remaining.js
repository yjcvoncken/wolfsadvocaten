(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  if (reduced.matches || !('IntersectionObserver' in window)) return;
  const elements = document.querySelectorAll('[data-enter], .reference-page .footer-main > *');
  const observer = new IntersectionObserver(entries => entries.forEach(({target, isIntersecting}) => {
    if (!isIntersecting) return;
    target.classList.remove('enter-pending');
    target.classList.add('enter-running');
    observer.unobserve(target);
    target.addEventListener('animationend', () => target.classList.remove('enter-running'), {once: true});
  }), {threshold: .05});
  elements.forEach(element => {
    if (element.dataset.enter === 'up') element.style.setProperty('--enter-y', '60px');
    element.classList.add('enter-pending');
    observer.observe(element);
  });
  reduced.addEventListener('change', () => {
    if (!reduced.matches) return;
    observer.disconnect();
    elements.forEach(element => element.classList.remove('enter-pending', 'enter-running'));
  });
})();
