(() => {
  const menu = document.querySelector('[data-naming-menu]');
  if (!menu) return;

  const trigger = menu.querySelector('[data-naming-menu-trigger]');
  const panel = menu.querySelector('[data-naming-menu-panel]');
  if (!trigger || !panel) return;

  const setOpen = (open) => {
    trigger.setAttribute('aria-expanded', String(open));
    panel.hidden = !open;
    menu.classList.toggle('is-open', open);
  };

  trigger.addEventListener('click', () => {
    setOpen(trigger.getAttribute('aria-expanded') !== 'true');
  });

  document.addEventListener('click', (event) => {
    if (!menu.contains(event.target)) setOpen(false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setOpen(false);
      trigger.focus();
    }
  });
})();
