(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const slides = [...document.querySelectorAll('.hero-slide')];
  let active = 0;
  let timer;
  function showSlide(step) {
    slides[active].classList.remove('active');
    active = (active + step + slides.length) % slides.length;
    slides[active].classList.add('active');
  }
  function startTimer() {
    clearInterval(timer);
    if (!reducedMotion.matches && !document.hidden) timer = setInterval(() => showSlide(1), 6500);
  }
  document.querySelector('.hero-next').addEventListener('click', () => { showSlide(1); startTimer(); });
  document.querySelector('.hero-prev').addEventListener('click', () => { showSlide(-1); startTimer(); });
  document.addEventListener('visibilitychange', startTimer);
  reducedMotion.addEventListener('change', startTimer);
  startTimer();

  // The reference uses one-time 60px float entrances with a 1.2s ease-in-out.
  const reveals = document.querySelectorAll('.home-hero h1, .home-about-copy .large-copy, .home-about-copy > p:nth-child(2), .home-method h2, .home-method p, .home-blog h2, .footer-main > *, .team-meta > *');
  if (reducedMotion.matches || !('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(({ target, isIntersecting }) => {
      if (!isIntersecting) return;
      target.classList.remove('reveal-pending');
      target.classList.add('reveal-running');
      observer.unobserve(target);
      target.addEventListener('animationend', () => target.classList.remove('reveal-running'), { once: true });
    });
  }, { threshold: 0.05 });
  reveals.forEach(element => {
    element.dataset.reveal = '';
    element.classList.add('reveal-pending');
    if (element.matches('.team-meta > a')) {
      element.style.setProperty('--reveal-x', '60px');
      element.style.setProperty('--reveal-y', '0px');
    } else if (element.matches('.team-meta h3, .team-meta p')) {
      element.style.setProperty('--reveal-y', '60px');
      element.style.setProperty('--reveal-duration', '1300ms');
    }
    observer.observe(element);
  });
  reducedMotion.addEventListener('change', () => {
    if (!reducedMotion.matches) return;
    observer.disconnect();
    reveals.forEach(element => element.classList.remove('reveal-pending', 'reveal-running'));
  });
})();
