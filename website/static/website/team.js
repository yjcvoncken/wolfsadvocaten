(() => {
  const teamNames = [...document.querySelectorAll('.team-list .team-meta h3')];
  function fitTeamName(heading) {
    heading.style.removeProperty('font-size');
    const name = heading.querySelector('a');
    const available = heading.clientWidth;
    if (!name || !available) return;
    const width = name.getBoundingClientRect().width;
    if (width > available) {
      const size = parseFloat(getComputedStyle(heading).fontSize);
      heading.style.fontSize = `${Math.floor(size * available / width * 100) / 100}px`;
    }
  }
  const fitTeamNames = () => teamNames.forEach(fitTeamName);
  fitTeamNames();
  document.fonts.ready.then(fitTeamNames);
  if ('ResizeObserver' in window) {
    const nameResizeObserver = new ResizeObserver(fitTeamNames);
    teamNames.forEach(heading => nameResizeObserver.observe(heading.parentElement));
  } else {
    window.addEventListener('resize', fitTeamNames);
  }

})();
