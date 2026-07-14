(() => {
  const links = Array.from(document.querySelectorAll('[data-adjust-feelings]'));
  if (!links.length) return;

  links.forEach((link) => {
    link.addEventListener('click', (event) => {
      const current = new URL(window.location.href);
      const target = new URL(link.getAttribute('href'), window.location.href);
      target.search = current.search;
      event.preventDefault();
      window.location.assign(target.toString());
    });
  });
})();
