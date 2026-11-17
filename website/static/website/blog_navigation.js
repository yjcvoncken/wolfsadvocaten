document.querySelectorAll('.blog-category-more').forEach(details => {
  document.addEventListener('click', event => {
    if (!details.contains(event.target)) details.open = false;
  });
  details.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      details.open = false;
      details.querySelector('summary').focus();
    }
  });
});
