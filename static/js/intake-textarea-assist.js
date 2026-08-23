(function () {
  // Starter chip text per question ID — shared across all verticals.
  var STARTERS = {
    // Business
    business_description: ["We help\u2026", "A platform that\u2026", "We make\u2026", "Founded to\u2026"],
    notes:                ["We\u2019re based in\u2026", "Our edge is\u2026", "We\u2019re different because\u2026"],
    partner_alignment:    ["We\u2019re torn between\u2026", "One partner prefers\u2026", "It needs to feel\u2026"],
    // Baby — notes and partner_alignment shared keys with business but different context;
    // vertical is distinguished by surrounding form class.
    // Pet
    pet_details:          ["They\u2019re always\u2026", "People say they look like\u2026", "Their quirk is\u2026"],
  };

  // Baby-specific overrides (baby form has class "baby-intake-form")
  var BABY_STARTERS = {
    notes:             ["We love names that\u2026", "It needs to feel\u2026", "Family tradition of\u2026"],
    partner_alignment: ["One of us likes\u2026", "We keep going back to\u2026", "We\u2019re split between\u2026"],
  };

  // Encouragement thresholds
  var ENCOURAGEMENT = [
    { min: 100, text: "Great context \u2014 more detail = sharper names \u2713", level: "strong" },
    { min: 60,  text: "Good detail \u2014 this helps \u2713",                    level: "good"   },
    { min: 30,  text: "Good start \u2713",                                        level: "start"  },
  ];

  var isBabyForm = Boolean(document.querySelector(".baby-intake-form"));

  function startersFor(questionId) {
    if (isBabyForm && BABY_STARTERS[questionId]) return BABY_STARTERS[questionId];
    return STARTERS[questionId] || null;
  }

  function encouragementFor(len) {
    for (var i = 0; i < ENCOURAGEMENT.length; i++) {
      if (len >= ENCOURAGEMENT[i].min) return ENCOURAGEMENT[i];
    }
    return null;
  }

  function buildChips(textarea, chips) {
    var wrap = document.createElement("div");
    wrap.className = "textarea-starters";
    wrap.setAttribute("aria-label", "Try a starter phrase");

    chips.forEach(function (text) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "textarea-starter-chip";
      btn.textContent = text;
      btn.addEventListener("click", function () {
        textarea.value = text;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.focus();
        // Place cursor at end
        var len = textarea.value.length;
        textarea.setSelectionRange(len, len);
        wrap.hidden = true;
      });
      wrap.appendChild(btn);
    });

    return wrap;
  }

  function buildEncouragement() {
    var el = document.createElement("p");
    el.className = "textarea-encouragement";
    el.setAttribute("aria-live", "polite");
    el.hidden = true;
    return el;
  }

  function attachToTextarea(textarea) {
    var questionId = textarea.id;
    if (!questionId) return;

    var chips = startersFor(questionId);
    var actionsEl = textarea.nextElementSibling; // actions div sits right after textarea

    var chipsEl = null;
    if (chips) {
      chipsEl = buildChips(textarea, chips);
      // Hide immediately if field already has content
      chipsEl.hidden = Boolean(textarea.value.trim());
      textarea.parentNode.insertBefore(chipsEl, actionsEl);
    }

    var encourageEl = buildEncouragement();
    textarea.parentNode.insertBefore(encourageEl, actionsEl);

    textarea.addEventListener("input", function () {
      var val = textarea.value;
      var len = val.length;

      // Hide chips once user starts typing
      if (chipsEl) chipsEl.hidden = Boolean(val.trim());

      // Encouragement
      var match = encouragementFor(len);
      if (match) {
        encourageEl.textContent = match.text;
        encourageEl.dataset.level = match.level;
        encourageEl.hidden = false;
      } else {
        encourageEl.hidden = true;
      }
    });
  }

  // Find all guided textareas across baby / pet / business
  var SELECTORS = [
    "[data-baby-question] textarea",
    "[data-pet-question] textarea",
    "[data-business-question] textarea",
    // Legacy / product vertical
    "[data-product-question] textarea",
  ];

  SELECTORS.forEach(function (sel) {
    document.querySelectorAll(sel).forEach(attachToTextarea);
  });
})();
