(() => {
  const trigger = document.querySelector('.menu-pill');
  const panel = document.querySelector('#site-menu');
  const close = panel.querySelector('.menu-close');
  const background = [...document.querySelectorAll('header, main, footer')];
  function setMenu(open) {
    panel.hidden = !open;
    trigger.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('menu-open', open);
    background.forEach(element => { element.inert = open; });
    if (open) { panel.scrollTop = 0; close.focus({preventScroll:true}); }
    else trigger.focus({preventScroll:true});
  }
  trigger.addEventListener('click', () => setMenu(panel.hidden));
  close.addEventListener('click', () => setMenu(false));
  panel.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
  document.addEventListener('keydown', event => {
    if (panel.hidden) return;
    if (event.key === 'Escape') setMenu(false);
    if (event.key !== 'Tab') return;
    const items = [...panel.querySelectorAll('button, a[href]')];
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
})();
