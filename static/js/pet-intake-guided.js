(function () {
  "use strict";

  // Only activates on Pet guided conversation forms.
  // Completely separate from baby-intake-polish.js — Baby is never touched by this file.
  const form = document.querySelector(".pet-conversation.pet-guided");
  if (!form) return;

  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const loadingHandoff = { delay: 650 };

  // All question sections in DOM order (matches intake_questions config order)
  const questions = Array.from(form.querySelectorAll("[data-pet-question]"));
  const header = form.querySelector("[data-pet-interview-header]");
  const progressBar = form.querySelector("[data-pet-progressbar]");
  const progressFill = form.querySelector("[data-pet-progress-fill]");
  const progressCopy = form.querySelector("[data-pet-progress-copy]");
  const confirmation = form.querySelector("[data-pet-confirmation]");
  const stage = form.querySelector("[data-pet-question-stage]");
  const directionReview = form.querySelector("[data-pet-direction-review]");
  const directionList = form.querySelector("[data-pet-direction-list]");
  const completePanel = form.querySelector("[data-pet-complete]");

  let activeId = null;
  let transitionTimer = null;
  let completing = false;
  let editingFromReview = false;

  // Gentle encouragement copy — Pet voice: playful, warm, personality-led
  const copy = {
    choiceRequired: "Nice — that helps us picture them.",
    choiceOptional: "Good to know — that gives us something to work with.",
    textWithContent: "That's helpful — we'll use it to shape their name.",
    textBlank: "No worries — let's keep going.",
  };

  // ── Helpers ────────────────────────────────────────────────────────────────

  function controlFor(question) {
    if (question.dataset.questionKind === "choice") {
      return question.querySelector("input.pet-native-control");
    }
    return question.querySelector(
      "textarea, input:not([type='hidden']):not(.pet-native-control):not([data-other-input])"
    );
  }

  function valueFor(question) {
    if (question.dataset.questionKind === "choice") {
      const control = question.querySelector("input.pet-native-control");
      if (!control) return "";
      if (control.value === "Other") {
        return (question.querySelector("[data-other-input]")?.value || "").trim();
      }
      return control.value.trim();
    }
    const control = controlFor(question);
    return control ? control.value.trim() : "";
  }

  function labelFor(question) {
    return question.querySelector("h2")?.textContent?.trim() || question.dataset.questionId;
  }

  function answerDisplay(question) {
    const value = valueFor(question);
    if (!value) return "";
    return value.length > 60 ? `${value.slice(0, 57)}\u2026` : value;
  }

  function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = value;
    return node.innerHTML;
  }

  // ── Progress ───────────────────────────────────────────────────────────────

  function updateProgress(question) {
    const index = Math.max(0, questions.indexOf(question));
    const number = index + 1;
    const total = questions.length;
    if (progressCopy) progressCopy.textContent = "Question " + number + " of " + total;
    if (progressBar) {
      progressBar.setAttribute("aria-valuenow", String(number));
      progressBar.setAttribute("aria-valuemax", String(total));
    }
    if (progressFill) {
      progressFill.style.width = ((number / total) * 100) + "%";
    }
  }

  // ── Focus ──────────────────────────────────────────────────────────────────

  function focusQuestion(question) {
    const target = question.querySelector(
      "[data-choice-value].is-selected, [data-choice-value], textarea, " +
      "input:not([type='hidden']):not(.pet-native-control):not([data-other-input])"
    );
    if (target) target.focus({ preventScroll: true });
  }

  // ── Show / hide ────────────────────────────────────────────────────────────

  function showQuestion(question) {
    if (!question || completing) return;
    window.clearTimeout(transitionTimer);
    activeId = question.dataset.questionId;

    questions.forEach(function (item) {
      const isActive = item === question;
      item.hidden = !isActive;
      item.classList.toggle("is-active", isActive);
    });

    if (directionReview) directionReview.hidden = true;
    if (completePanel) completePanel.hidden = true;
    if (stage) stage.hidden = false;
    if (header) header.hidden = false;

    updateProgress(question);
    // Show inline Back on Q2+, hide on Q1
    var isFirstQ = questions.indexOf(question) === 0;
    form.querySelectorAll('[data-pet-nav-back]').forEach(function(btn) { btn.hidden = isFirstQ; });
    window.requestAnimationFrame(function () { focusQuestion(question); });
  }

  function nextQuestion(question) {
    const index = questions.indexOf(question);
    return questions[index + 1] || null;
  }

  function previousQuestion(question) {
    const index = questions.indexOf(question);
    return index > 0 ? questions[index - 1] : null;
  }

  // ── Confirmation message ───────────────────────────────────────────────────

  function showConfirmation(text, callback) {
    window.clearTimeout(transitionTimer);
    if (confirmation) confirmation.textContent = text;
    transitionTimer = window.setTimeout(function () {
      if (confirmation) confirmation.textContent = "";
      if (callback) callback();
    }, motionQuery.matches ? 0 : 300);
  }

  // ── Advance ────────────────────────────────────────────────────────────────

  function advanceFrom(question, confirmText) {
    showConfirmation(confirmText, function () {
      if (editingFromReview) {
        editingFromReview = false;
        showDirectionReview();
      } else {
        const next = nextQuestion(question);
        if (next) showQuestion(next);
        else showDirectionReview();
      }
    });
  }

  // ── Direction review ───────────────────────────────────────────────────────

  function renderDirectionReview() {
    if (!directionList) return;
    directionList.replaceChildren();

    questions.forEach(function (question) {
      const answer = answerDisplay(question);

      const dt = document.createElement("dt");
      dt.textContent = labelFor(question);

      const dd = document.createElement("dd");

      const answerSpan = document.createElement("span");
      answerSpan.textContent = answer || "Not answered";
      answerSpan.className = answer ? "pet-direction-answer" : "pet-direction-blank";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "pet-direction-edit";
      editBtn.dataset.editQuestion = question.dataset.questionId;
      editBtn.textContent = "Edit";

      dd.appendChild(answerSpan);
      dd.appendChild(editBtn);
      directionList.appendChild(dt);
      directionList.appendChild(dd);
    });
  }

  function showDirectionReview() {
    window.clearTimeout(transitionTimer);
    questions.forEach(function (q) { q.hidden = true; q.classList.remove("is-active"); });
    if (stage) stage.hidden = true;
    if (completePanel) completePanel.hidden = true;
    renderDirectionReview();
    if (directionReview) directionReview.hidden = false;
    if (header) header.hidden = false;
    if (progressCopy) progressCopy.textContent = "Your direction";
    if (progressFill) progressFill.style.width = "100%";
    if (progressBar) {
      progressBar.setAttribute("aria-valuenow", String(questions.length));
      progressBar.setAttribute("aria-valuemax", String(questions.length));
    }
    window.requestAnimationFrame(function () {
      var findBtn = directionReview ? directionReview.querySelector("[data-pet-direction-find]") : null;
      if (findBtn) findBtn.focus({ preventScroll: true });
    });
  }

  // ── Finish / submit ────────────────────────────────────────────────────────

  function finishInterview() {
    completing = true;
    questions.forEach(function (q) { q.hidden = true; });
    if (directionReview) directionReview.hidden = true;
    if (stage) stage.hidden = true;
    if (completePanel) completePanel.hidden = false;
    if (header) header.hidden = false;
    if (progressFill) progressFill.style.width = "100%";
    // Dispatch the canonical finish-interview event so progress.js
    // can show the overlay before submitting. Never call .submit() directly.
    // See contract comment at top of progress.js.
    window.setTimeout(function () {
      form.dispatchEvent(new CustomEvent("namengine:finish-interview", { bubbles: true }));
    }, motionQuery.matches ? 100 : loadingHandoff.delay);
  }

  // ── Next button handler ────────────────────────────────────────────────────

  function handleNext(question) {
    const kind = question.dataset.questionKind;
    const required = question.dataset.required === "true";

    if (kind === "choice") {
      const nativeControl = question.querySelector("input.pet-native-control");
      const nativeValue = nativeControl ? nativeControl.value : "";
      // Required with no selection at all
      if (required && !nativeValue) {
        if (confirmation) confirmation.textContent = "Please make a selection to continue.";
        return;
      }
      // Other selected but nothing typed
      if (nativeValue === "Other") {
        const otherVal = (question.querySelector("[data-other-input]") ? question.querySelector("[data-other-input]").value : "").trim();
        if (!otherVal) {
          if (confirmation) confirmation.textContent = "Please enter your answer to continue.";
          const oi = question.querySelector("[data-other-input]");
          if (oi) oi.focus();
          return;
        }
      }
      const val = valueFor(question);
      advanceFrom(question, val ? copy.choiceOptional : copy.textBlank);
      return;
    }

    // Text / textarea
    if (required && !valueFor(question)) {
      if (confirmation) confirmation.textContent = "Please share an answer to continue.";
      const input = question.querySelector(
        "textarea, input:not([type='hidden']):not(.pet-native-control):not([data-other-input])"
      );
      if (input) input.focus();
      return;
    }
    advanceFrom(question, valueFor(question) ? copy.textWithContent : copy.textBlank);
  }

  // ── Initial state ──────────────────────────────────────────────────────────

  function syncInitialSelections() {
    questions.forEach(function (question) {
      const control = question.querySelector("input.pet-native-control");
      if (!control || question.dataset.questionKind !== "choice") return;
      question.querySelectorAll("[data-choice-value]").forEach(function (button) {
        const selected = button.dataset.choiceValue === control.value;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-checked", String(selected));
      });
    });
  }

  function startInterview() {
    document.body.classList.add("pet-interview-started");
    showQuestion(questions[0]);
    form.scrollIntoView({ behavior: motionQuery.matches ? "auto" : "smooth", block: "start" });
  }

  // ── Event handlers ─────────────────────────────────────────────────────────

  // Choice card selections: pet-choice-cards.js handles visual state and fires change on native control.
  // We listen for that change event to trigger auto-advance for required questions.
  form.addEventListener("change", function (event) {
    const control = event.target.closest("input.pet-native-control");
    if (!control) return;
    const question = control.closest("[data-pet-question]");
    if (!question || question.dataset.questionKind !== "choice") return;
    const value = control.value;
    // Auto-advance for all choice questions (required and optional) when a real value is selected
    if (value && value !== "Other") {
      advanceFrom(question, question.dataset.required === "true" ? copy.choiceRequired : copy.choiceOptional);
    }
  });

  form.addEventListener("click", function (event) {
    // Back button
    if (event.target.closest("[data-pet-nav-back]")) {
      if (!document.body.classList.contains("pet-interview-started")) return;
      event.preventDefault();
      window.clearTimeout(transitionTimer);
      if (confirmation) confirmation.textContent = "";

      // Back from direction review → last question
      if (directionReview && !directionReview.hidden) {
        editingFromReview = false;
        const lastQuestion = questions[questions.length - 1];
        if (lastQuestion) showQuestion(lastQuestion);
        return;
      }

      const activeQuestion = questions.find(function (q) {
        return q.dataset.questionId === activeId && !q.hidden;
      });
      const previous = activeQuestion ? previousQuestion(activeQuestion) : null;
      if (previous) showQuestion(previous);
      return;
    }

    // Next button
    if (event.target.closest("[data-pet-next]")) {
      const question = event.target.closest("[data-pet-question]");
      if (question) handleNext(question);
      return;
    }

    // Edit from direction review
    const editBtn = event.target.closest("[data-edit-question]");
    if (editBtn) {
      const question = questions.find(function (q) {
        return q.dataset.questionId === editBtn.dataset.editQuestion;
      });
      if (question) {
        editingFromReview = true;
        if (directionReview) directionReview.hidden = true;
        if (stage) stage.hidden = false;
        showQuestion(question);
      }
      return;
    }

    // Find names button
    if (event.target.closest("[data-pet-direction-find]")) {
      finishInterview();
      return;
    }
  });

  // Enter key on text inputs advances to next question
  form.addEventListener("keydown", function (event) {
    if (
      event.key === "Enter" &&
      event.target.matches(
        "input:not([type='hidden']):not(.pet-native-control), textarea"
      )
    ) {
      event.preventDefault();
      const question = event.target.closest("[data-pet-question]");
      if (question) handleNext(question);
    }
  });

  // Prevent native form submit unless completing
  form.addEventListener("submit", function (event) {
    if (!completing) event.preventDefault();
  });

  // Begin button (uses .baby-begin-button from shared welcome section;
  // safe on Pet pages because baby-intake-polish.js bails out without .baby-conversation)
  const begin = document.querySelector(".baby-begin-button");
  if (begin) {
    begin.addEventListener("click", function (event) {
      event.preventDefault();
      startInterview();
    });
  }

  // ── Pet-type choice enrichment: emoji icon + personality descriptor ────────

  const petTypeEmoji = {
    "Dog":     { emoji: "🐕", descriptor: "Loyal, playful, full of personality" },
    "Cat":     { emoji: "🐈", descriptor: "Independent, curious, a little mysterious" },
    "Horse":   { emoji: "🐴", descriptor: "Majestic, powerful, deeply bonded" },
    "Bird":    { emoji: "🦜", descriptor: "Feathered, expressive, vocal" },
    "Rabbit":  { emoji: "🐰", descriptor: "Soft, curious, unexpectedly funny" },
    "Reptile": { emoji: "🦎", descriptor: "Cool, calm, their own kind of personality" },
    "Other":   { emoji: "🐾", descriptor: "Every companion deserves a great name" },
  };

  function enrichPetTypeChoices() {
    const petTypeQ = questions.find(function (q) {
      return q.dataset.questionId === "pet_type";
    });
    if (!petTypeQ) return;
    petTypeQ.querySelectorAll("[data-choice-value]").forEach(function (card) {
      const value = card.dataset.choiceValue;
      const meta = petTypeEmoji[value];
      if (!meta) return;
      // Avoid double-enrichment
      if (card.querySelector(".pet-choice-icon")) return;
      // Build icon tile
      const icon = document.createElement("span");
      icon.className = "pet-choice-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = meta.emoji;
      // Add descriptor under the strong label
      const copyEl = card.querySelector(".pet-choice-copy");
      if (copyEl) {
        const descriptor = document.createElement("small");
        descriptor.className = "pet-choice-descriptor";
        descriptor.textContent = meta.descriptor;
        copyEl.appendChild(descriptor);
      }
      // Prepend icon before copy
      card.insertBefore(icon, card.firstChild);
    });
  }

  // ── Init ───────────────────────────────────────────────────────────────────

  document.body.classList.add("pet-interview-enhanced");
  syncInitialSelections();
  enrichPetTypeChoices();
  if (window.location.hash === "#pet-intake-form") startInterview();
})();
