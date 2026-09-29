/* vc-hover.js — hover "Start naming" span to reveal info card; clicking anywhere on card navigates
   v=20260929-v4 */

(function () {
  'use strict';

  const cards = Array.from(document.querySelectorAll('.landing-vertical-card'));

  /* ── Clicking anywhere on the card navigates ── */
  cards.forEach(card => {
    card.addEventListener('click', e => {
      e.stopPropagation();
      window.location.href = card.getAttribute('href');
    });
  });

  /* ── Desktop: hover "Start naming →" span to reveal popup ── */
  if (window.matchMedia('(hover: hover)').matches) {

    cards.forEach(card => {
      const trigger = Array.from(card.children).find(el => el.tagName === 'SPAN');
      const vcHover = card.querySelector('.vc-hover');
      if (!trigger || !vcHover) return;

      let hideTimer;

      function show() {
        clearTimeout(hideTimer);
        card.classList.add('vc-active');
      }

      function scheduleHide() {
        hideTimer = setTimeout(() => card.classList.remove('vc-active'), 120);
      }

      trigger.addEventListener('mouseenter', show);
      trigger.addEventListener('mouseleave', scheduleHide);
      vcHover.addEventListener('mouseenter', show);
      vcHover.addEventListener('mouseleave', scheduleHide);
    });

  } else {
    /* ── Mobile: tap "Start naming" span to reveal; vc-nav-btn navigates; outside dismisses ── */

    function dismissAll() {
      cards.forEach(c => c.classList.remove('vc-active'));
    }

    cards.forEach(card => {
      const trigger = Array.from(card.children).find(el => el.tagName === 'SPAN');
      if (!trigger) return;

      trigger.addEventListener('click', e => {
        e.stopPropagation();
        e.preventDefault();
        if (!card.classList.contains('vc-active')) {
          dismissAll();
          card.classList.add('vc-active');
        }
      });
    });

    document.addEventListener('click', e => {
      if (!e.target.closest('.landing-vertical-card')) dismissAll();
    });
  }

})();
