(() => {
  const menus = document.querySelectorAll('[data-naming-menu]');
  if (!menus.length) return;

  const closeMenu = (menu) => {
    const trigger = menu.querySelector('[data-naming-menu-trigger]');
    const panel = menu.querySelector('[data-naming-menu-panel]');
    if (!trigger || !panel) return;
    trigger.setAttribute('aria-expanded', 'false');
    panel.hidden = true;
  };

  const openMenu = (menu) => {
    const trigger = menu.querySelector('[data-naming-menu-trigger]');
    const panel = menu.querySelector('[data-naming-menu-panel]');
    if (!trigger || !panel) return;
    menus.forEach((item) => {
      if (item !== menu) closeMenu(item);
    });
    trigger.setAttribute('aria-expanded', 'true');
    panel.hidden = false;
  };

  menus.forEach((menu) => {
    const trigger = menu.querySelector('[data-naming-menu-trigger]');
    const panel = menu.querySelector('[data-naming-menu-panel]');
    if (!trigger || !panel) return;

    trigger.addEventListener('click', () => {
      const expanded = trigger.getAttribute('aria-expanded') === 'true';
      expanded ? closeMenu(menu) : openMenu(menu);
    });

    menu.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeMenu(menu);
        trigger.focus();
      }
    });
  });

  document.addEventListener('click', (event) => {
    menus.forEach((menu) => {
      if (!menu.contains(event.target)) closeMenu(menu);
    });
  });
})();
