(function () {
  const form = document.querySelector(".baby-intake-form");
  if (!form) return;

  if (!form.classList.contains("baby-conversation")) {
    const sections = Array.from(form.querySelectorAll("[data-baby-intake-section]"));
    sections.forEach((section) => section.classList.toggle("is-complete", section.checkValidity()));
    return;
  }

  const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  // Keep the established loading handoff copy/timing contract available to the flow.
  const loadingHandoff = { label: "Building your naming profile", delay: 650 };
  const questionOrder = [
    "gender", "style", "familiarity_preference", "discovery_style",
    "timeless_vs_distinctive", "sound", "cultural_context", "cultural_heritage",
    "family_context", "notes", "partner_alignment", "avoid", "priority_focus"
  ];
  const orderIndex = new Map(questionOrder.map((id, index) => [id, index]));
  const questions = Array.from(form.querySelectorAll("[data-baby-question]"))
    .sort((left, right) => (orderIndex.get(left.dataset.questionId) ?? 99) - (orderIndex.get(right.dataset.questionId) ?? 99));
  const history = form.querySelector("[data-baby-answer-history]");
  const historyList = form.querySelector("[data-baby-answer-list]");
  const progressTitle = form.querySelector("[data-baby-progress-title]");
  const progressCopy = form.querySelector("[data-baby-progress-copy]");
  const progressBar = form.querySelector("[data-baby-progressbar]");
  const progressFill = form.querySelector("[data-baby-progress-fill]");
  const confirmation = form.querySelector("[data-baby-confirmation]");
  const completePanel = form.querySelector("[data-baby-complete]");
  const stage = form.querySelector("[data-baby-question-stage]");
  const journeyStages = Array.from(form.querySelectorAll("[data-baby-journey-stage]"));
  const checkIn = form.querySelector("[data-intake-checkin]");
  const checkInHeading = form.querySelector("[data-checkin-heading]");
  const checkInCopy = form.querySelector("[data-checkin-copy]");
  const checkInOptions = form.querySelector("[data-checkin-options]");
  const checkInBack = form.querySelector("[data-checkin-back]");
  const checkInReturn = form.querySelector("[data-checkin-return]");
  const directionReview = form.querySelector("[data-baby-direction-review]");
  const directionList = form.querySelector("[data-baby-direction-list]");
  const journeyCopyConfigurations = {
    baby: {
      fallback: "Let’s get to know your family.",
      completion: "Almost there.",
      questions: {
        gender: "Let’s get to know your family.",
        style: "We’re discovering the kinds of names you’ll love.",
        familiarity_preference: "We’re discovering the kinds of names you’ll love.",
        discovery_style: "We’re discovering the kinds of names you’ll love.",
        timeless_vs_distinctive: "We’re narrowing in on the right fit.",
        sound: "We’re narrowing in on the right fit.",
        cultural_context: "We’re narrowing in on the right fit.",
        cultural_heritage: "We’re narrowing in on the right fit.",
        family_context: "We're refining your best-fit names.",
        partner_alignment: "We're refining your best-fit names.",
        avoid: "We're refining your best-fit names.",
        notes: "Almost there.",
        priority_focus: "Almost there."
      }
    }
  };
  const journeyCopy = journeyCopyConfigurations[form.dataset.journeyVertical] || journeyCopyConfigurations.baby;
  const intakeStepConfigurations = {
    baby: {
      checkIns: [{
        id: "midpoint",
        insertAfter: "sound",
        heading: "Are we asking the right questions?",
        supportingCopy: "We want to understand what matters most to you before suggesting names.",
        journeyTitle: "We’re narrowing in on the right fit.",
        storageKey: "namengine:intake-checkin:baby:midpoint:v1",
        responses: [
          { key: "yes", label: "Yes, these questions make sense" },
          { key: "mostly", label: "Mostly" },
          { key: "unsure", label: "I’m not sure yet" }
        ]
      }]
    }
  };
  const intakeStepConfiguration = intakeStepConfigurations[form.dataset.journeyVertical] || { checkIns: [] };
  const checkInConfiguration = intakeStepConfiguration.checkIns[0] || null;
  const skipped = new Set();
  let activeId = null;
  let transitionTimer = null;
  let completing = false;
  let editingFromReview = false;
  let checkInResponse = readCheckInResponse();
  let checkInAdvancing = false;

  function readCheckInResponse() {
    if (!checkInConfiguration) return "";
    try {
      const stored = JSON.parse(window.sessionStorage.getItem(checkInConfiguration.storageKey) || "null");
      return checkInConfiguration.responses.some((response) => response.key === stored?.response) ? stored.response : "";
    } catch (_error) {
      return "";
    }
  }

  function persistCheckInResponse(response) {
    try {
      window.sessionStorage.setItem(checkInConfiguration.storageKey, JSON.stringify({ response }));
    } catch (_error) {
      // In-memory state still preserves the response when storage is unavailable.
    }
  }

  function renderCheckInConfiguration() {
    if (!checkInConfiguration || !checkIn) return;
    checkIn.dataset.checkinId = checkInConfiguration.id;
    checkIn.dataset.insertAfter = checkInConfiguration.insertAfter;
    checkInHeading.textContent = checkInConfiguration.heading;
    checkInCopy.textContent = checkInConfiguration.supportingCopy;
    checkInOptions.replaceChildren();
    checkInConfiguration.responses.forEach((response) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "baby-choice baby-checkin-choice";
      button.dataset.checkinValue = response.key;
      button.setAttribute("role", "radio");
      button.setAttribute("aria-checked", String(checkInResponse === response.key));
      button.innerHTML = `<span class="baby-choice-copy"><strong>${escapeHtml(response.label)}</strong></span><span class="baby-choice-chevron" aria-hidden="true">›</span><span class="baby-choice-mark" aria-hidden="true">✓</span>`;
      button.classList.toggle("is-selected", checkInResponse === response.key);
      checkInOptions.appendChild(button);
    });
  }

  function controlFor(question) {
    return question.querySelector("select, textarea, input:not([data-other-input])");
  }

  function valueFor(question) {
    const control = controlFor(question);
    if (!control) return "";
    if (control.value === "Other") {
      return (question.querySelector("[data-other-input]")?.value || "").trim();
    }
    return control.value.trim();
  }

  function syncTextActionState(question) {
    if (!question || question.dataset.questionKind === "choice") return;
    const skip = question.querySelector("[data-baby-skip]");
    if (!skip) return;
    const hasAnswer = Boolean(valueFor(question));
    skip.textContent = "Next";
    skip.dataset.actionState = hasAnswer ? "next" : "skip";
    skip.setAttribute("aria-label", hasAnswer ? "Save this answer and continue" : "Continue to next question");
  }

  function syncAllTextActionStates() {
    questions.forEach(syncTextActionState);
  }

  function isApplicable(question) {
    const dependency = question.dataset.conditionField;
    if (!dependency) return true;
    const source = questions.find((item) => item.dataset.questionId === dependency);
    return Boolean(question.dataset.conditionCurrent || (source && valueFor(source) === question.dataset.conditionValue));
  }

  function applicableQuestions() {
    return questions.filter(isApplicable);
  }

  function clearQuestion(question) {
    const control = controlFor(question);
    if (control) control.value = "";
    const other = question.querySelector("[data-other-input]");
    if (other) {
      other.value = "";
      other.disabled = true;
      const otherWrap = other.closest("[data-baby-other-wrap]");
      if (otherWrap) otherWrap.hidden = true;
    }
    question.querySelectorAll("[data-choice-value]").forEach((button) => {
      button.classList.remove("is-selected");
      button.setAttribute("aria-checked", "false");
    });
    delete question.dataset.conditionCurrent;
    skipped.delete(question.dataset.questionId);
  }

  function clearDependentConditionOverrides(question) {
    questions
      .filter((item) => item.dataset.conditionField === question.dataset.questionId)
      .forEach((item) => { delete item.dataset.conditionCurrent; });
  }

  function syncConditions() {
    questions.filter((question) => !isApplicable(question)).forEach(clearQuestion);
  }

  function answerLabel(question) {
    const value = valueFor(question);
    if (!value) return skipped.has(question.dataset.questionId) ? "Skipped" : "";
    return value.length > 58 ? `${value.slice(0, 55)}…` : value;
  }

  function answeredBefore(question) {
    if (!question) return [];
    const applicable = applicableQuestions();
    const activeIndex = applicable.indexOf(question);
    return applicable.slice(0, Math.max(0, activeIndex)).filter((item) => valueFor(item) || skipped.has(item.dataset.questionId));
  }

  function renderHistory(question) {
    if (!history || !historyList) return;
    const priorAnswers = answeredBefore(question);
    history.hidden = priorAnswers.length === 0;
    historyList.replaceChildren();
    priorAnswers.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "baby-answer-chip";
      button.dataset.editAnswer = item.dataset.questionId;
      button.innerHTML = `<span aria-hidden="true">✓</span><span>${escapeHtml(answerLabel(item))}</span><small>Edit</small>`;
      historyList.appendChild(button);
    });
  }

  function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = value;
    return node.innerHTML;
  }

  function updateProgress(question) {
    const applicable = applicableQuestions();
    const index = Math.max(0, applicable.indexOf(question));
    const number = index + 1;
    const total = applicable.length;
    progressTitle.textContent = journeyCopy.questions[question.dataset.questionId] || journeyCopy.fallback;
    progressCopy.textContent = `Question ${number} of ${total}`;
    progressBar.setAttribute("aria-valuenow", String(number));
    progressBar.setAttribute("aria-valuemax", String(total));
    progressFill.style.width = `${(number / total) * 100}%`;
    updateJourney(question);
  }

  function updateJourney(question) {
    const activeStage = journeyStages.findIndex((item) => item.dataset.stageName === question.dataset.questionSection);
    journeyStages.forEach((item, index) => {
      item.classList.toggle("is-active", index === activeStage);
      item.classList.toggle("is-complete", index < activeStage);
      if (index === activeStage) item.setAttribute("aria-current", "step");
      else item.removeAttribute("aria-current");
    });
  }

  function checkInAnchorQuestion() {
    return questions.find((question) => question.dataset.questionId === checkInConfiguration?.insertAfter) || null;
  }

  function checkInFollowingQuestion() {
    const anchor = checkInAnchorQuestion();
    return anchor ? nextQuestion(anchor) : null;
  }

  function focusQuestion(question) {
    const target = question.querySelector("[data-choice-value].is-selected, [data-choice-value], textarea, input:not([type='hidden'])");
    if (target) target.focus({ preventScroll: true });
  }

  function showQuestion(question, options) {
    if (!question || completing) return;
    window.clearTimeout(transitionTimer);
    form.classList.remove("is-checkin-active");
    activeId = question.dataset.questionId;
    questions.forEach((item) => {
      const isActive = item === question;
      item.hidden = !isActive;
      item.classList.toggle("is-active", isActive);
    });
    if (checkIn) checkIn.hidden = true;
    if (checkInReturn) {
      checkInReturn.hidden = !(checkInResponse && question === checkInFollowingQuestion());
    }
    progressCopy.hidden = false;
    stage.hidden = false;
    completePanel.hidden = true;
    if (directionReview) directionReview.hidden = true;
    renderHistory(question);
    updateProgress(question);
    syncTextActionState(question);
    // Show inline Back on Q2+, hide on Q1
    const isFirstQ = applicableQuestions().indexOf(question) === 0;
    form.querySelectorAll('[data-baby-nav-back]').forEach((btn) => { btn.hidden = isFirstQ; });
    // Move progress gauge into active question — ONE element in DOM, JS moves it on each change.
    // For Baby: place ABOVE the choice list / input so it’s always visible regardless of choice count.
    const progressEl = form.querySelector('.baby-question-progress');
    if (progressEl) {
      const insertBefore = question.querySelector('.baby-choice-list') ||
                           question.querySelector('textarea') ||
                           question.querySelector('input:not([type="hidden"]):not([data-other-input])') ||
                           question.querySelector('.baby-question-actions');
      if (insertBefore) insertBefore.before(progressEl);
      else question.appendChild(progressEl);
    }
    if (options?.focus !== false) window.requestAnimationFrame(() => focusQuestion(question));
  }

  function moveProgressToRoot() {
    // Move progress back to its DOM root position (before baby-journey nav) when not in a question.
    const progressEl = form.querySelector('.baby-question-progress');
    const journeyNav = form.querySelector('.baby-journey');
    if (progressEl && journeyNav) journeyNav.before(progressEl);
  }

  function showCheckIn() {
    if (!checkInConfiguration || !checkIn || completing) return;
    window.clearTimeout(transitionTimer);
    form.classList.add("is-checkin-active");
    checkInAdvancing = false;
    questions.forEach((question) => {
      question.hidden = true;
      question.classList.remove("is-active");
    });
    moveProgressToRoot();
    renderCheckInConfiguration();
    checkIn.hidden = false;
    checkIn.classList.add("is-active");
    checkInReturn.hidden = true;
    stage.hidden = false;
    completePanel.hidden = true;
    if (directionReview) directionReview.hidden = true;
    progressTitle.textContent = checkInConfiguration.journeyTitle;
    progressCopy.hidden = true;
    const anchor = checkInAnchorQuestion();
    if (anchor) {
      renderHistory(checkInFollowingQuestion());
      updateJourney(anchor);
    }
    window.requestAnimationFrame(() => checkIn.querySelector("[data-checkin-value].is-selected, [data-checkin-value]")?.focus({ preventScroll: true }));
  }

  function nextQuestion(question) {
    syncConditions();
    const applicable = applicableQuestions();
    const index = applicable.indexOf(question);
    return applicable[index + 1] || null;
  }

  function previousQuestion(question) {
    syncConditions();
    const applicable = applicableQuestions();
    const index = applicable.indexOf(question);
    return index > 0 ? applicable[index - 1] : null;
  }

  function labelFor(question) {
    return question.querySelector("h2")?.textContent?.trim() || question.dataset.questionId;
  }

  function renderDirectionReview() {
    if (!directionList) return;
    directionList.replaceChildren();
    applicableQuestions().forEach((question) => {
      const value = valueFor(question);
      const display = value ? (value.length > 60 ? value.slice(0, 57) + "\u2026" : value) : "";
      const dt = document.createElement("dt");
      dt.textContent = labelFor(question);
      const dd = document.createElement("dd");
      const answerSpan = document.createElement("span");
      answerSpan.textContent = display || "Not answered";
      answerSpan.className = display ? "baby-direction-answer" : "baby-direction-blank";
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "baby-direction-edit";
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
    form.classList.remove("is-checkin-active");
    questions.forEach((q) => { q.hidden = true; q.classList.remove("is-active"); });
    moveProgressToRoot();
    if (checkIn) checkIn.hidden = true;
    if (history) history.hidden = true;
    stage.hidden = true;
    completePanel.hidden = true;
    renderDirectionReview();
    if (directionReview) directionReview.hidden = false;
    progressTitle.textContent = "Your naming direction";
    progressCopy.textContent = "Ready to find your name";
    progressCopy.hidden = false;
    progressFill.style.width = "100%";
    progressBar.setAttribute("aria-valuenow", progressBar.getAttribute("aria-valuemax"));
    window.requestAnimationFrame(() => {
      const findBtn = directionReview ? directionReview.querySelector("[data-baby-direction-find]") : null;
      if (findBtn) findBtn.focus({ preventScroll: true });
    });
  }

  function goBackOneStep(event) {
    if (!document.body.classList.contains("baby-interview-started")) return;
    event.preventDefault();
    window.clearTimeout(transitionTimer);
    confirmation.textContent = "";
    if (directionReview && !directionReview.hidden) {
      editingFromReview = false;
      const applicable = applicableQuestions();
      const lastQuestion = applicable[applicable.length - 1];
      if (lastQuestion) showQuestion(lastQuestion);
      return;
    }
    const activeQuestion = questions.find((question) => question.dataset.questionId === activeId && !question.hidden);
    const previous = activeQuestion ? previousQuestion(activeQuestion) : (checkIn && !checkIn.hidden ? checkInAnchorQuestion() : null);
    if (!previous) return;
    showQuestion(previous);
  }

  function confirmAndAdvance(question, label) {
    confirmation.textContent = label ? `Saved — ${label}` : "Saved";
    question.classList.add("is-confirmed");
    transitionTimer = window.setTimeout(() => {
      question.classList.remove("is-confirmed");
      confirmation.textContent = "";
      if (editingFromReview) {
        editingFromReview = false;
        showDirectionReview();
        return;
      }
      const next = nextQuestion(question);
      if (checkInConfiguration && question.dataset.questionId === checkInConfiguration.insertAfter && !checkInResponse) showCheckIn();
      else if (next) showQuestion(next);
      else showDirectionReview();
    }, motionQuery.matches ? 0 : 260);
  }

  function finishInterview() {
    completing = true;
    form.classList.remove("is-checkin-active");
    questions.forEach((question) => { question.hidden = true; });
    moveProgressToRoot();
    history.hidden = true;
    stage.hidden = true;
    progressTitle.textContent = journeyCopy.completion;
    progressCopy.textContent = "Interview complete";
    progressFill.style.width = "100%";
    progressBar.setAttribute("aria-valuenow", progressBar.getAttribute("aria-valuemax"));
    completePanel.hidden = false;
    // Dispatch the canonical finish-interview event so progress.js
    // can show the overlay before submitting. Never call .submit() directly.
    // See contract comment at top of progress.js.
    window.setTimeout(() => form.dispatchEvent(new CustomEvent("namengine:finish-interview", { bubbles: true })), motionQuery.matches ? 100 : loadingHandoff.delay);
  }

  function selectChoice(question, button) {
    const control = controlFor(question);
    const value = button.dataset.choiceValue;

    // Toggle: clicking an already-selected card on an optional question deselects it.
    if (button.classList.contains("is-selected") && question.dataset.required !== "true") {
      question.querySelectorAll("[data-choice-value]").forEach((choice) => {
        choice.classList.remove("is-selected");
        choice.setAttribute("aria-checked", "false");
      });
      control.value = "";
      control.dispatchEvent(new Event("change", { bubbles: true }));
      skipped.delete(question.dataset.questionId);
      clearDependentConditionOverrides(question);
      // Reset taste-strength to defaults when priority focus is deselected.
      if (question.dataset.questionId === "priority_focus") {
        [34, 33, 33].forEach((val, idx) => {
          const field = form.querySelector(`[data-baby-priority-field="${idx}"]`);
          if (field) field.value = val;
        });
      }
      const otherWrapD = question.querySelector("[data-baby-other-wrap]");
      const otherInputD = question.querySelector("[data-other-input]");
      if (otherWrapD) otherWrapD.hidden = true;
      if (otherInputD) otherInputD.disabled = true;
      syncTextActionState(question);
      return;
    }

    question.querySelectorAll("[data-choice-value]").forEach((choice) => {
      const selected = choice === button;
      choice.classList.toggle("is-selected", selected);
      choice.setAttribute("aria-checked", String(selected));
    });
    control.value = value;
    control.dispatchEvent(new Event("change", { bubbles: true }));
    skipped.delete(question.dataset.questionId);
    clearDependentConditionOverrides(question);

    const otherWrap = question.querySelector("[data-baby-other-wrap]");
    const otherInput = question.querySelector("[data-other-input]");
    if (otherWrap) otherWrap.hidden = value !== "Other";
    if (otherInput) otherInput.disabled = value !== "Other";
    if (value === "Other" && otherInput) {
      otherInput.focus();
      return;
    }
    // When the priority focus question is answered, propagate weights to hidden taste-strength inputs.
    if (question.dataset.questionId === "priority_focus") {
      const weights = (button.dataset.babyPriorityWeights || "34,33,33").split(",").map(Number);
      form.querySelectorAll("[data-baby-priority-field]").forEach((field) => {
        const idx = parseInt(field.dataset.babyPriorityField, 10);
        if (!isNaN(idx) && idx < weights.length) field.value = weights[idx];
      });
    }
    confirmAndAdvance(question, value);
  }

  function continueText(question) {
    const control = controlFor(question);
    if (question.dataset.required === "true" && !control.value.trim()) {
      confirmation.textContent = "Share an answer to continue.";
      control.focus();
      return;
    }
    skipped.delete(question.dataset.questionId);
    confirmAndAdvance(question, valueFor(question));
  }

  function skipQuestion(question) {
    clearDependentConditionOverrides(question);
    clearQuestion(question);
    skipped.add(question.dataset.questionId);
    confirmAndAdvance(question, "Skipped");
  }

  function selectCheckInResponse(button) {
    if (checkInAdvancing) return;
    checkInAdvancing = true;
    checkInResponse = button.dataset.checkinValue;
    persistCheckInResponse(checkInResponse);
    checkInOptions.querySelectorAll("[data-checkin-value]").forEach((choice) => {
      const selected = choice === button;
      choice.classList.toggle("is-selected", selected);
      choice.setAttribute("aria-checked", String(selected));
    });
    confirmation.textContent = "Saved";
    transitionTimer = window.setTimeout(() => {
      confirmation.textContent = "";
      const following = checkInFollowingQuestion();
      if (following) showQuestion(following);
      else showDirectionReview();
    }, motionQuery.matches ? 0 : 260);
  }

  function syncInitialSelections() {
    questions.forEach((question) => {
      const control = controlFor(question);
      if (!control || question.dataset.questionKind !== "choice") return;
      question.querySelectorAll("[data-choice-value]").forEach((button) => {
        const selected = button.dataset.choiceValue === control.value;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-checked", String(selected));
      });
    });
  }

  form.addEventListener("click", (event) => {
    const navBack = event.target.closest("[data-baby-nav-back]");
    if (navBack) {
      goBackOneStep(event);
      return;
    }
    const checkInChoice = event.target.closest("[data-checkin-value]");
    if (checkInChoice) {
      selectCheckInResponse(checkInChoice);
      return;
    }
    if (event.target.closest("[data-checkin-back]")) {
      const anchor = checkInAnchorQuestion();
      if (anchor) showQuestion(anchor);
      return;
    }
    if (event.target.closest("[data-checkin-return]")) {
      showCheckIn();
      return;
    }
    const choice = event.target.closest("[data-choice-value]");
    if (choice) {
      selectChoice(choice.closest("[data-baby-question]"), choice);
      return;
    }
    const edit = event.target.closest("[data-edit-answer]");
    if (edit) {
      const question = questions.find((item) => item.dataset.questionId === edit.dataset.editAnswer);
      if (question) showQuestion(question);
      return;
    }
    if (event.target.closest("[data-baby-direction-find]")) {
      finishInterview();
      return;
    }
    const dirEdit = event.target.closest("[data-edit-question]");
    if (dirEdit) {
      const editTarget = questions.find((q) => q.dataset.questionId === dirEdit.dataset.editQuestion);
      if (editTarget) {
        editingFromReview = true;
        if (directionReview) directionReview.hidden = true;
        stage.hidden = false;
        showQuestion(editTarget);
      }
      return;
    }
    const question = event.target.closest("[data-baby-question]");
    if (!question) return;
    if (event.target.closest("[data-baby-continue]")) continueText(question);
    if (event.target.closest("[data-baby-skip]")) {
      if (question.dataset.questionKind !== "choice" && valueFor(question)) continueText(question);
      else skipQuestion(question);
    }
    if (event.target.closest("[data-baby-other-continue]")) {
      const other = question.querySelector("[data-other-input]");
      if (!other.value.trim()) {
        confirmation.textContent = "Tell us what you have in mind.";
        other.focus();
      } else {
        confirmAndAdvance(question, other.value.trim());
      }
    }
  });

  form.addEventListener("input", (event) => {
    const question = event.target.closest("[data-baby-question]");
    if (question) syncTextActionState(question);
  });

  form.addEventListener("keydown", (event) => {
    const choice = event.target.closest("[data-choice-value]");
    if (choice && ["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(event.key)) {
      event.preventDefault();
      const buttons = Array.from(choice.closest("[data-baby-choices]").querySelectorAll("[data-choice-value]"));
      const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
      buttons[(buttons.indexOf(choice) + direction + buttons.length) % buttons.length].focus();
    }
    if (event.key === "Enter" && event.target.matches("textarea, input:not([data-other-input])")) {
      event.preventDefault();
      continueText(event.target.closest("[data-baby-question]"));
    }
  });

  form.addEventListener("submit", (event) => {
    if (!completing) event.preventDefault();
  });

  const begin = document.querySelector(".baby-begin-button");
  function startInterview() {
    document.body.classList.add("baby-interview-started");
    const requested = form.dataset.editQuestion;
    const editQuestion = questions.find((question) => question.dataset.questionId === requested && isApplicable(question));
    const firstUnanswered = applicableQuestions().find((question) => !valueFor(question));
    showQuestion(editQuestion || firstUnanswered || applicableQuestions()[0]);
    window.scrollTo({ top: 0, behavior: motionQuery.matches ? "auto" : "smooth" });
  }
  begin?.addEventListener("click", (event) => {
    event.preventDefault();
    startInterview();
  });

  document.body.classList.add("baby-interview-enhanced");
  renderCheckInConfiguration();
  syncInitialSelections();
  syncConditions();
  syncAllTextActionStates();
  if (form.dataset.editQuestion || window.location.hash === "#baby-intake-form") startInterview();
})();
