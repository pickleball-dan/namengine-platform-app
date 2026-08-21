(function () {
  "use strict";

  // Only activates on Business guided conversation forms.
  // Completely separate from baby-intake-polish.js and pet-intake-guided.js.
  const form = document.querySelector(".business-conversation.business-guided");
  if (!form) return;

  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const loadingHandoff = { delay: 650 };

  const questions = Array.from(form.querySelectorAll("[data-business-question]"));
  const header = form.querySelector("[data-business-interview-header]");
  const progressBar = form.querySelector("[data-business-progressbar]");
  const progressFill = form.querySelector("[data-business-progress-fill]");
  const progressCopy = form.querySelector("[data-business-progress-copy]");
  const confirmation = form.querySelector("[data-business-confirmation]");
  const stage = form.querySelector("[data-business-question-stage]");
  const directionReview = form.querySelector("[data-business-direction-review]");
  const directionList = form.querySelector("[data-business-direction-list]");
  const completePanel = form.querySelector("[data-business-complete]");

  let activeId = null;
  let transitionTimer = null;
  let completing = false;
  let editingFromReview = false;

  // Gentle encouragement copy — Business voice: confident, strategic, clear
  const copy = {
    choiceRequired: "Good — that shapes the strategic brief.",
    choiceOptional: "Noted — that helps sharpen the direction.",
    textWithContent: "Clear. We'll factor that into the names.",
    textBlank: "No problem — let's keep going.",
  };

  // ── Helpers ────────────────────────────────────────────────────────────────

  function controlFor(question) {
    if (question.dataset.questionKind === "choice") {
      return question.querySelector("input.business-native-control");
    }
    return question.querySelector(
      "textarea, input:not([type='hidden']):not(.business-native-control):not([data-other-input])"
    );
  }

  function valueFor(question) {
    if (question.dataset.questionKind === "priority") {
      const selected = question.querySelector("[data-choice-value].is-selected");
      if (!selected) return "";
      return selected.querySelector("strong")?.textContent?.trim() || selected.dataset.choiceValue || "";
    }
    if (question.dataset.questionKind === "choice") {
      const control = question.querySelector("input.business-native-control");
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
    return value.length > 60 ? value.slice(0, 57) + "\u2026" : value;
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
    if (progressFill) progressFill.style.width = ((number / total) * 100) + "%";
  }

  // ── Focus ──────────────────────────────────────────────────────────────────

  function focusQuestion(question) {
    const target = question.querySelector(
      "[data-choice-value].is-selected, [data-choice-value], textarea, " +
      "input:not([type='hidden']):not(.business-native-control):not([data-other-input])"
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
    form.querySelectorAll('[data-business-nav-back]').forEach(function(btn) { btn.hidden = isFirstQ; });
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

  // ── Confirmation ───────────────────────────────────────────────────────────

  function showConfirmation(text, callback) {
    window.clearTimeout(transitionTimer);
    if (confirmation) confirmation.textContent = text;
    transitionTimer = window.setTimeout(function () {
      if (confirmation) confirmation.textContent = "";
      if (callback) callback();
    }, motionQuery.matches ? 0 : 300);
  }

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
      answerSpan.className = answer ? "business-direction-answer" : "business-direction-blank";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "business-direction-edit";
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
      var findBtn = directionReview ? directionReview.querySelector("[data-business-direction-find]") : null;
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

  // ── Next handler ───────────────────────────────────────────────────────────

  function handleNext(question) {
    const kind = question.dataset.questionKind;
    const required = question.dataset.required === "true";

    if (kind === "priority") {
      advanceFrom(question, copy.textBlank);
      return;
    }

    if (kind === "choice") {
      const nativeControl = question.querySelector("input.business-native-control");
      const nativeValue = nativeControl ? nativeControl.value : "";
      if (required && !nativeValue) {
        if (confirmation) confirmation.textContent = "Please make a selection to continue.";
        return;
      }
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

    if (required && !valueFor(question)) {
      if (confirmation) confirmation.textContent = "Please share an answer to continue.";
      const input = question.querySelector(
        "textarea, input:not([type='hidden']):not(.business-native-control):not([data-other-input])"
      );
      if (input) input.focus();
      return;
    }
    advanceFrom(question, valueFor(question) ? copy.textWithContent : copy.textBlank);
  }

  // ── Init ───────────────────────────────────────────────────────────────────

  function syncInitialSelections() {
    questions.forEach(function (question) {
      const control = question.querySelector("input.business-native-control");
      if (!control || question.dataset.questionKind !== "choice") return;
      question.querySelectorAll("[data-choice-value]").forEach(function (button) {
        const selected = button.dataset.choiceValue === control.value;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-checked", String(selected));
      });
    });
  }

  function startInterview() {
    document.body.classList.add("business-interview-started");
    showQuestion(questions[0]);
    form.scrollIntoView({ behavior: motionQuery.matches ? "auto" : "smooth", block: "start" });
  }

  // ── Event listeners ────────────────────────────────────────────────────────

  // pet-choice-cards.js handles visual state and fires change on native control.
  // We listen for that change event to auto-advance required choice questions.
  form.addEventListener("change", function (event) {
    const control = event.target.closest("input.business-native-control");
    if (!control) return;
    const question = control.closest("[data-business-question]");
    if (!question || question.dataset.questionKind !== "choice") return;
    const value = control.value;
    if (value && value !== "Other") {
      advanceFrom(question, question.dataset.required === "true" ? copy.choiceRequired : copy.choiceOptional);
    }
  });

  form.addEventListener("click", function (event) {
    // Back
    if (event.target.closest("[data-business-nav-back]")) {
      if (!document.body.classList.contains("business-interview-started")) return;
      event.preventDefault();
      window.clearTimeout(transitionTimer);
      if (confirmation) confirmation.textContent = "";

      if (directionReview && !directionReview.hidden) {
        editingFromReview = false;
        showQuestion(questions[questions.length - 1]);
        return;
      }

      const activeQuestion = questions.find(function (q) {
        return q.dataset.questionId === activeId && !q.hidden;
      });
      const previous = activeQuestion ? previousQuestion(activeQuestion) : null;
      if (previous) showQuestion(previous);
      return;
    }

    // Next
    if (event.target.closest("[data-business-next]")) {
      const question = event.target.closest("[data-business-question]");
      if (question) handleNext(question);
      return;
    }

    // Priority question choice (no native control — handled here directly)
    const priorityChoice = event.target.closest("[data-priority-weights]");
    if (priorityChoice) {
      const question = priorityChoice.closest("[data-business-question]");
      if (question && question.dataset.questionKind === "priority") {
        question.querySelectorAll("[data-choice-value]").forEach(function (c) {
          const sel = c === priorityChoice;
          c.classList.toggle("is-selected", sel);
          c.setAttribute("aria-checked", String(sel));
        });
        const weights = (priorityChoice.dataset.priorityWeights || "34,33,33").split(",");
        form.querySelectorAll("[data-business-priority-field]").forEach(function (field, i) {
          if (i < weights.length) field.value = weights[i].trim();
        });
        advanceFrom(question, copy.choiceRequired);
        return;
      }
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

    // Find names
    if (event.target.closest("[data-business-direction-find]")) {
      finishInterview();
      return;
    }
  });

  // Enter key on text inputs
  form.addEventListener("keydown", function (event) {
    if (
      event.key === "Enter" &&
      event.target.matches(
        "input:not([type='hidden']):not(.business-native-control), textarea"
      )
    ) {
      event.preventDefault();
      const question = event.target.closest("[data-business-question]");
      if (question) handleNext(question);
    }
  });

  form.addEventListener("submit", function (event) {
    if (!completing) event.preventDefault();
  });

  const begin = document.querySelector(".baby-begin-button");
  if (begin) {
    begin.addEventListener("click", function (event) {
      event.preventDefault();
      startInterview();
    });
  }

  document.body.classList.add("business-interview-enhanced");
  syncInitialSelections();
  if (window.location.hash === "#business-intake-form") startInterview();
})();
