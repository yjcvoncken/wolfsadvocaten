(() => {
  const manager = document.querySelector('#photo-manager');
  if (!manager) return;
  const cards = [...manager.querySelectorAll('.photo-card')];
  const search = manager.querySelector('#photo-search');
  const category = manager.querySelector('#photo-category');
  function filterPhotos() {
    const query = search.value.toLocaleLowerCase().trim();
    let count = 0;
    cards.forEach(card => {
      const visible = (!category.value || card.dataset.category === category.value)
        && card.dataset.search.toLocaleLowerCase().includes(query);
      card.hidden = !visible;
      if (visible) count++;
    });
    manager.querySelector('#photo-count').textContent = `${count} photo slots`;
    manager.querySelector('#photo-no-results').hidden = count !== 0;
  }
  search.addEventListener('input', filterPhotos);
  category.addEventListener('change', filterPhotos);

  cards.forEach(card => {
    const input = card.querySelector('.photo-file');
    if (!input) return;
    const frame = card.querySelector('.photo-dropzone');
    const image = frame.querySelector('img');
    const status = card.querySelector('.photo-status');
    const save = card.querySelector('button[type="submit"]');
    const cropX = card.elements.center_x;
    const cropY = card.elements.center_y;
    let previewUrl;
    let dragging;
    let dragDepth = 0;
    let saving = false;
    save.disabled = true;
    function message(text, error = false) {
      status.textContent = text;
      status.classList.toggle('is-error', error);
    }
    function updatePosition(x, y) {
      cropX.value = Math.max(0, Math.min(1, x));
      cropY.value = Math.max(0, Math.min(1, y));
      image.style.objectPosition = `${cropX.value * 100}% ${cropY.value * 100}%`;
    }
    function choosePhoto(file) {
      if (!file || saving) return;
      if (!file.type.startsWith('image/')) {
        message('Please choose an image file.', true);
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(file);
      image.onload = () => {
        image.hidden = false;
        frame.querySelector('.photo-empty').hidden = true;
        frame.classList.add('is-pending');
        updatePosition(.5, .5);
        save.disabled = false;
        message('Ready to save. Drag the preview to adjust the crop.');
      };
      image.onerror = () => {
        save.disabled = true;
        message('This image could not be opened. Please choose another photo.', true);
      };
      image.src = previewUrl;
    }
    input.addEventListener('change', () => choosePhoto(input.files[0]));
    frame.addEventListener('dragenter', event => {
      event.preventDefault();
      if (!saving) { dragDepth++; frame.classList.add('is-over'); }
    });
    frame.addEventListener('dragover', event => { event.preventDefault(); event.dataTransfer.dropEffect = saving ? 'none' : 'copy'; });
    frame.addEventListener('dragleave', () => { if (--dragDepth <= 0) frame.classList.remove('is-over'); });
    frame.addEventListener('drop', event => {
      event.preventDefault();
      dragDepth = 0;
      frame.classList.remove('is-over');
      choosePhoto(event.dataTransfer.files[0]);
    });
    frame.addEventListener('pointerdown', event => {
      if (!frame.classList.contains('is-pending') || saving || event.button !== 0) return;
      const bounds = frame.getBoundingClientRect();
      const scale = Math.max(bounds.width / image.naturalWidth, bounds.height / image.naturalHeight);
      dragging = { x: event.clientX, y: event.clientY, cropX: +cropX.value, cropY: +cropY.value,
        overflowX: image.naturalWidth * scale - bounds.width, overflowY: image.naturalHeight * scale - bounds.height };
      frame.setPointerCapture(event.pointerId);
      frame.classList.add('is-dragging');
      event.preventDefault();
    });
    frame.addEventListener('pointermove', event => {
      if (!dragging) return;
      updatePosition(dragging.cropX - (dragging.overflowX > .5 ? (event.clientX - dragging.x) / dragging.overflowX : 0),
        dragging.cropY - (dragging.overflowY > .5 ? (event.clientY - dragging.y) / dragging.overflowY : 0));
    });
    function endDrag() { dragging = undefined; frame.classList.remove('is-dragging'); }
    frame.addEventListener('pointerup', endDrag);
    frame.addEventListener('pointercancel', endDrag);
    frame.addEventListener('keydown', event => {
      if (!frame.classList.contains('is-pending') || saving) return;
      const step = event.shiftKey ? .1 : .025;
      const changes = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
      if (!changes[event.key]) return;
      event.preventDefault();
      updatePosition(+cropX.value + changes[event.key][0], +cropY.value + changes[event.key][1]);
    });
    card.addEventListener('submit', async event => {
      event.preventDefault();
      if (!input.files.length || saving) return;
      saving = true;
      save.disabled = true;
      input.disabled = true;
      message('Saving photo…');
      // Disabled file inputs are omitted by FormData, so append the chosen upload explicitly.
      const data = new FormData(card);
      data.set('photo', input.files[0]);
      try {
        const response = await fetch(card.action, { method: 'POST', body: data,
          headers: { Accept: 'application/json' }, credentials: 'same-origin' });
        if (!response.headers.get('Content-Type')?.includes('application/json')) {
          throw new Error('Please reload the page, sign in if needed, and try again.');
        }
        const result = await response.json();
        if (!response.ok) throw new Error(result.errors?.join(' ') || 'The photo could not be saved.');
        image.onload = null;
        image.onerror = null;
        image.src = result.url;
        updatePosition(.5, .5);
        frame.classList.remove('is-pending');
        input.value = '';
        if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = undefined; }
        message('Saved. The new photo is now used on the website.');
      } catch (error) {
        message(error.message || 'The photo could not be saved. Please try again.', true);
        save.disabled = false;
      } finally {
        saving = false;
        input.disabled = false;
      }
    });
  });
})();
