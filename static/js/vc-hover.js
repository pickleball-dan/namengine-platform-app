/* vc-hover.js — hover "Start naming" span to reveal info card; card click blocked except action button
   v=20260922-v3 */

(function () {
  'use strict';

  const cards = Array.from(document.querySelectorAll('.landing-vertical-card'));

  /* ── Block card-level navigation everywhere — only vc-nav-btn navigates ── */
  cards.forEach(card => {
    card.addEventListener('click', e => {
      // Allow vc-nav-btn to navigate
      if (e.target.closest('.vc-nav-btn')) {
        e.stopPropagation();
        e.preventDefault();
        window.location.href = card.getAttribute('href');
        return;
      }
      // Allow vc-remind to scroll (handled below)
      if (e.target.closest('.vc-remind')) return;
      // Block everything else — no navigation
      e.preventDefault();
      e.stopPropagation();
    });
  });

  /* ── Remind spans: scroll rather than navigate ── */
  document.querySelectorAll('.vc-remind').forEach(el => {
    el.addEventListener('click', e => {
      e.stopPropagation();
      e.preventDefault();
      const target = document.getElementById('remind') ||
                     document.querySelector('[id*="remind"]');
      if (target) target.scrollIntoView({ behavior: 'smooth' });
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
