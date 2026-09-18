/**
 * homepage-return.js
 * Reads taste-history localStorage for all three verticals and renders a
 * "Pick up where you left off" section for returning users.
 *
 * Self-inserting: works standalone (before index.html has the hook div) and
 * when index.html has #homepage-return-hook already in the DOM.
 */
(function () {
  'use strict';

  var VERTICALS = [
    {
      slug: 'baby',
      eyebrow: 'Your evolving taste',
      accent: '#FE3360',
      logoSrc: '/static/images/namengine-baby.svg',
      logoAlt: 'NamEngine Baby',
    },
    {
      slug: 'pet',
      eyebrow: 'Your evolving pet-name taste',
      accent: '#F2B84B',
      logoSrc: '/static/images/namengine-pets.svg',
      logoAlt: 'NamEngine Pet',
    },
    {
      slug: 'business',
      eyebrow: 'Your emerging brand direction',
      accent: '#29344F',
      logoSrc: '/static/images/namengine-biz.svg',
      logoAlt: 'NamEngine Business',
    },
  ];

  function readHistory(slug) {
    try {
      var raw = window.localStorage.getItem('namengine.' + slug + '.tasteHistory.v1');
      var parsed = JSON.parse(raw || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
      return [];
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildCard(vertical, latest) {
    var names = latest.lovedNames.slice(0, 4);
    var overflow = latest.lovedNames.length > 4 ? ' +' + (latest.lovedNames.length - 4) + ' more' : '';
    var loved = names.map(escapeHtml).join(', ') + overflow;
    var viewBtn = latest.shareUrl
      ? '<a class="hpr-view" href="' + escapeHtml(latest.shareUrl) + '">View list</a>'
      : '';
    return (
      '<div class="hpr-card hpr-card--' + vertical.slug + '" style="--hpr-accent:' + vertical.accent + '">' +
        '<div class="hpr-card-logo">' +
          '<img src="' + escapeHtml(vertical.logoSrc) + '" alt="' + escapeHtml(vertical.logoAlt) + '">' +
        '</div>' +
        '<div class="hpr-card-body">' +
          '<p class="hpr-card-eyebrow">' + escapeHtml(vertical.eyebrow) + '</p>' +
          '<p class="hpr-loved"><span class="hpr-heart" aria-hidden="true">\u2665</span> ' + loved + '</p>' +
        '</div>' +
        '<div class="hpr-card-actions">' +
          '<a class="hpr-resume" href="' + escapeHtml(latest.listUrl) + '">Resume \u2192</a>' +
          viewBtn +
        '</div>' +
      '</div>'
    );
  }

  function injectStyles() {
    if (document.getElementById('hpr-styles')) return;
    var style = document.createElement('style');
    style.id = 'hpr-styles';
    style.textContent = [
      '.hpr-section{padding:2rem 1.25rem;border-bottom:1px solid rgba(255,255,255,.07);}',
      '.hpr-inner{max-width:960px;margin:0 auto;}',
      '.hpr-global-eyebrow{font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;opacity:.5;margin:0 0 .4rem;}',
      '.hpr-heading{font-size:1.25rem;font-weight:700;margin:0 0 1.25rem;line-height:1.3;}',
      '.hpr-cards{display:flex;flex-wrap:wrap;gap:.875rem;}',
      '.hpr-card{flex:1 1 240px;min-width:200px;max-width:360px;border:1px solid rgba(255,255,255,.09);border-radius:12px;padding:.9rem 1rem;background:rgba(255,255,255,.03);display:flex;flex-direction:column;gap:.5rem;}',
      '.hpr-card-logo img{height:20px;width:auto;opacity:.8;}',
      '.hpr-card-eyebrow{font-size:.65rem;letter-spacing:.1em;text-transform:uppercase;opacity:.5;margin:0;}',
      '.hpr-loved{font-size:.88rem;margin:0;opacity:.85;line-height:1.4;}',
      '.hpr-heart{color:var(--hpr-accent,#FE3360);}',
      '.hpr-card-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.2rem;}',
      '.hpr-resume{background:var(--hpr-accent,#FE3360);color:#fff;font-size:.8rem;font-weight:600;padding:.4rem .9rem;border-radius:6px;text-decoration:none;white-space:nowrap;}',
      '.hpr-resume:hover{opacity:.85;}',
      '.hpr-view{font-size:.8rem;font-weight:500;padding:.4rem .8rem;border-radius:6px;text-decoration:none;border:1px solid rgba(255,255,255,.18);color:inherit;opacity:.65;white-space:nowrap;}',
      '.hpr-view:hover{opacity:1;}',
      '@media(max-width:600px){.hpr-card{max-width:100%;}}',
    ].join('');
    document.head.appendChild(style);
  }

  function getOrCreateContainer() {
    var container = document.getElementById('homepage-return-hook');
    if (container) return container;

    // Self-insert before the "naming-experiences" section when the div
    // isn't yet in the template (demo/test mode).
    container = document.createElement('div');
    container.id = 'homepage-return-hook';
    container.hidden = true;
    var anchor = document.getElementById('naming-experiences');
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(container, anchor);
    } else {
      // Fallback: after the hero section
      var hero = document.querySelector('.landing-hero');
      if (hero && hero.parentNode) {
        hero.parentNode.insertBefore(container, hero.nextSibling);
      }
    }
    return container;
  }

  function render() {
    var sessions = [];
    for (var i = 0; i < VERTICALS.length; i++) {
      var v = VERTICALS[i];
      var history = readHistory(v.slug);
      var withNames = history.filter(function (h) {
        return Array.isArray(h.lovedNames) && h.lovedNames.length > 0;
      });
      if (withNames.length > 0) {
        sessions.push({ vertical: v, latest: withNames[0] });
      }
    }

    var container = getOrCreateContainer();
    if (!sessions.length) {
      container.hidden = true;
      container.innerHTML = '';
      return;
    }

    injectStyles();
    var cards = sessions.map(function (s) { return buildCard(s.vertical, s.latest); }).join('');
    container.innerHTML =
      '<section class="hpr-section" aria-label="Continue your naming session">' +
        '<div class="hpr-inner">' +
          '<p class="hpr-global-eyebrow">Welcome back</p>' +
          '<h2 class="hpr-heading">Pick up where you left off</h2>' +
          '<div class="hpr-cards">' + cards + '</div>' +
        '</div>' +
      '</section>';
    container.hidden = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }

  // Expose for testing
  window.NamEngineHomepageReturn = { render: render };
})();
