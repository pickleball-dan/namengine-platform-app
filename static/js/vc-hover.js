/* vc-hover.js — hover on "Start naming" span to reveal info card
   v=20260824-v2 */

(function () {
  'use strict';

  const cards = Array.from(document.querySelectorAll('.landing-vertical-card'));

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

  /* ── Desktop: hover "Start naming →" span to reveal ── */
  if (window.matchMedia('(hover: hover)').matches) {

    cards.forEach(card => {
      // The direct-child span is "Start naming →"
      const trigger = Array.from(card.children).find(el => el.tagName === 'SPAN');
      const vcHover = card.querySelector('.vc-hover');
      if (!trigger || !vcHover) return;

      let hideTimer;

      function show() {
        clearTimeout(hideTimer);
        card.classList.add('vc-active');
      }

      function scheduleHide() {
        // Small grace period so mouse can travel from span → hover box
        hideTimer = setTimeout(() => card.classList.remove('vc-active'), 120);
      }

      trigger.addEventListener('mouseenter', show);
      trigger.addEventListener('mouseleave', scheduleHide);
      vcHover.addEventListener('mouseenter', show);
      vcHover.addEventListener('mouseleave', scheduleHide);

      /* Nav button on desktop: click navigates */
      const navBtn = vcHover.querySelector('.vc-nav-btn');
      if (navBtn) {
        navBtn.addEventListener('click', e => {
          e.stopPropagation();
          e.preventDefault();
          window.location.href = card.getAttribute('href');
        });
      }
    });

  } else {
    /* ── Mobile: first tap reveals, nav button navigates, outside dismisses ── */

    function dismissAll() {
      cards.forEach(c => c.classList.remove('vc-active'));
    }

    cards.forEach(card => {
      card.addEventListener('click', e => {
        if (e.target.closest('.vc-remind')) return;
        if (e.target.closest('.vc-nav-btn')) {
          e.stopPropagation();
          e.preventDefault();
          window.location.href = card.getAttribute('href');
          return;
        }
        if (!card.classList.contains('vc-active')) {
          e.preventDefault();
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
