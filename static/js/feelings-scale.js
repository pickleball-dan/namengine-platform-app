(() => {
  const babyFinalForm = document.querySelector('[data-baby-final-form]');
  if (babyFinalForm) {
    const question = babyFinalForm.querySelector('[data-baby-final-question]');
    const complete = babyFinalForm.querySelector('[data-baby-final-complete]');
    const status = babyFinalForm.querySelector('[data-baby-final-status]');
    const inputs = Array.from(babyFinalForm.querySelectorAll('[data-feelings-input]'));
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let chosen = false;

    function completeAndSubmit(message) {
      status.textContent = message;
      window.setTimeout(() => {
        question.hidden = true;
        complete.hidden = false;
        window.setTimeout(() => babyFinalForm.requestSubmit(), reduceMotion.matches ? 100 : 650);
      }, reduceMotion.matches ? 0 : 260);
    }

    babyFinalForm.addEventListener('click', (event) => {
      const skip = event.target.closest('[data-baby-final-skip]');
      const button = event.target.closest('[data-baby-weight]');
      if (chosen || (!button && !skip)) return;
      chosen = true;
      if (skip) {
        completeAndSubmit('Using a thoughtful balance.');
        return;
      }
      babyFinalForm.querySelectorAll('[data-baby-weight]').forEach((choice) => {
        const selected = choice === button;
        choice.classList.toggle('is-selected', selected);
        choice.setAttribute('aria-checked', String(selected));
      });
      button.dataset.babyWeight.split(',').forEach((weight, index) => {
        if (inputs[index]) inputs[index].value = weight;
      });
      const label = button.dataset.babyLabel || button.querySelector('.baby-choice-copy strong, span')?.textContent || 'your direction';
      completeAndSubmit(`Saved — ${label}`);
    });
    return;
  }

  const scale = document.querySelector('[data-feelings-scale]');
  if (!scale) return;

  const orb = scale.querySelector('[data-feelings-orb]');
  const rows = Array.from(scale.querySelectorAll('[data-feelings-row]'));
  const inputs = rows.map((row) => row.querySelector('[data-feelings-input]'));
  const fills = rows.map((row) => row.querySelector('[data-feelings-fill]'));
  const labels = rows.map((row) => row.querySelector('[data-feelings-label]'));
  const count = rows.length;

  const anchorSets = {
    2: [
      { x: 0.18, y: 0.18 },
      { x: 0.82, y: 0.82 },
    ],
    3: [
      { x: 0.12, y: 0.14 },
      { x: 0.88, y: 0.14 },
      { x: 0.5, y: 0.88 },
    ],
    4: [
      { x: 0.12, y: 0.14 },
      { x: 0.88, y: 0.14 },
      { x: 0.12, y: 0.86 },
      { x: 0.88, y: 0.86 },
    ],
  };
  const anchors = (anchorSets[count] || anchorSets[3]).slice(0, count);

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function numericInput(input, fallback) {
    const value = Number(input && input.value);
    return Number.isFinite(value) ? clamp(value, 0, 100) : fallback;
  }

  function friendly(value) {
    if (value >= 68) return 'Primary';
    if (value >= 46) return 'Strong';
    if (value >= 25) return 'Balanced';
    if (value >= 12) return 'Light';
    return 'Quiet';
  }

  function normalizeWeights(weights) {
    const clean = weights.map((weight) => clamp(Math.round(weight), 0, 100));
    const total = clean.reduce((sum, item) => sum + item, 0);
    if (!total) return clean.map((_, index) => (index === 0 ? 100 : 0));

    const normalized = clean.map((item) => Math.round((item / total) * 100));
    normalized[normalized.length - 1] += 100 - normalized.reduce((sum, item) => sum + item, 0);
    return normalized;
  }

  function updateUrl(weights) {
    const url = new URL(window.location.href);
    inputs.forEach((input, index) => {
      if (input && input.name) {
        url.searchParams.set(input.name, String(weights[index]));
      }
    });
    window.history.replaceState(window.history.state, '', url.toString());
  }

  function applyWeights(weights, persist = true) {
    const normalized = normalizeWeights(weights);
    normalized.forEach((weight, index) => {
      if (inputs[index]) inputs[index].value = String(weight);
      if (fills[index]) fills[index].style.width = `${weight}%`;
      if (labels[index]) labels[index].textContent = friendly(weight);
    });
    if (persist) updateUrl(normalized);
    return normalized;
  }

  function positionFromWeights(weights) {
    const normalized = normalizeWeights(weights);
    const total = normalized.reduce((sum, item) => sum + item, 0) || 1;
    return normalized.reduce(
      (point, weight, index) => {
        const influence = weight / total;
        point.x += anchors[index].x * influence;
        point.y += anchors[index].y * influence;
        return point;
      },
      { x: 0, y: 0 }
    );
  }

  function setOrbPosition(x, y) {
    orb.style.setProperty('--x', `${clamp(x, 0, 1) * 100}%`);
    orb.style.setProperty('--y', `${clamp(y, 0, 1) * 100}%`);
  }

  function weightsFromPoint(x, y) {
    const raw = anchors.map((point) => {
      const distance = Math.hypot(x - point.x, y - point.y);
      return 1 / Math.pow(distance + 0.12, 2);
    });
    const total = raw.reduce((sum, item) => sum + item, 0) || 1;
    return raw.map((item) => (item / total) * 100);
  }

  function updateFromPointer(clientX, clientY) {
    const rect = orb.getBoundingClientRect();
    const x = clamp((clientX - rect.left) / rect.width, 0, 1);
    const y = clamp((clientY - rect.top) / rect.height, 0, 1);
    setOrbPosition(x, y);
    applyWeights(weightsFromPoint(x, y));
  }

  let dragging = false;
  orb.addEventListener('pointerdown', (event) => {
    dragging = true;
    orb.setPointerCapture(event.pointerId);
    updateFromPointer(event.clientX, event.clientY);
  });
  orb.addEventListener('pointermove', (event) => {
    if (dragging) updateFromPointer(event.clientX, event.clientY);
  });
  orb.addEventListener('pointerup', () => { dragging = false; });
  orb.addEventListener('pointercancel', () => { dragging = false; });

  const startingWeights = applyWeights(
    inputs.map((input, index) => numericInput(input, index === 0 ? 34 : 33)),
    false
  );
  const startingPoint = positionFromWeights(startingWeights);
  setOrbPosition(startingPoint.x, startingPoint.y);
})();
