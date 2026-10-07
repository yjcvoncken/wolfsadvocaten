(() => {
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  if (motion.matches || !('IntersectionObserver' in window)) return;
  // Animate content inside the cards; the cards themselves retain native sticky positioning.
  const elements = document.querySelectorAll('.about-intro h1, .about-introduction, .about-story h2, .about-story .about-copy, .about-network-grid article > *, .about-networks > h2, .about-team-heading h2, .about-person-info, .footer-main > *');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.remove('about-enter-pending');
      entry.target.classList.add('about-enter-running');
      observer.unobserve(entry.target);
      entry.target.addEventListener('animationend', () => entry.target.classList.remove('about-enter-running'), { once: true });
    });
  }, { threshold: 0.05 });
  elements.forEach(element => {
    if (element.matches('.about-introduction, .about-copy, .about-network-grid article > *')) element.style.setProperty('--enter-y', '60px');
    if (element.matches('.about-network-grid h3')) element.style.setProperty('--enter-duration', '1300ms');
    element.classList.add('about-enter-pending');
    observer.observe(element);
  });
  motion.addEventListener('change', () => {
    if (!motion.matches) return;
    observer.disconnect();
    elements.forEach(element => element.classList.remove('about-enter-pending', 'about-enter-running'));
  });
})();
