/* landing-hero.js — Floating header + vertical card hover windows
   v=20260824-hover-v2 */

(function () {
  'use strict';

  /* ── Scroll listener: transparent → solid header ── */
  const header = document.querySelector('.site-header');
  if (header) {
    const getThreshold = () => window.innerHeight * 0.75;
    const onScroll = () => {
      header.classList.toggle('scrolled', window.scrollY > getThreshold());
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── Vertical pills → direct navigation ── */
  document.querySelectorAll('.landing-pill[data-vertical]').forEach(btn => {
    btn.addEventListener('click', () => {
      window.location.href = '/' + btn.dataset.vertical;
    });
  });

  /* ── Hero CTA → baby ── */
  const heroCta = document.querySelector('[data-hero-cta]');
  if (heroCta) {
    heroCta.addEventListener('click', () => { window.location.href = '/baby'; });
  }

  /* ── Remind spans: stop propagation, scroll to remind section ── */
  document.querySelectorAll('.vc-remind').forEach(el => {
    el.addEventListener('click', e => {
      e.stopPropagation();
      e.preventDefault();
      const target = document.getElementById('remind') ||
                     document.querySelector('.landing-hero-remind');
      if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
  });

  /* ── Mobile: tap to reveal, nav button to go ── */
  const isTouch = window.matchMedia('(hover: none)').matches;

  if (isTouch) {
    const cards = Array.from(document.querySelectorAll('.landing-vertical-card'));

    function dismissAll() {
      cards.forEach(c => c.classList.remove('vc-active'));
    }

    cards.forEach(card => {
      card.addEventListener('click', e => {
        /* Remind handled above — do nothing here */
        if (e.target.closest('.vc-remind')) return;
        /* Nav button: navigate to vertical */
        if (e.target.closest('.vc-nav-btn')) {
          e.stopPropagation();
          e.preventDefault();
          window.location.href = card.getAttribute('href');
          return;
        }
        /* First tap: reveal hover window */
        if (!card.classList.contains('vc-active')) {
          e.preventDefault();
          dismissAll();
          card.classList.add('vc-active');
        }
        /* Second tap anywhere else on an active card: navigate */
      });
    });

    /* Tap outside any card → dismiss */
    document.addEventListener('click', e => {
      if (!e.target.closest('.landing-vertical-card')) {
        dismissAll();
      }
    });
  }

})();
