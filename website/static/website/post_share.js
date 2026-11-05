document.querySelectorAll('[data-copy-link]').forEach((button) => {
  button.hidden = false;
  button.addEventListener('click', async () => {
    const status = button.parentElement.querySelector('[role="status"]');
    status.textContent = '';
    try {
      await navigator.clipboard.writeText(button.dataset.copyLink);
      status.textContent = button.dataset.copied;
    } catch {
      window.prompt(button.dataset.copyPrompt, button.dataset.copyLink);
    }
  });
});
