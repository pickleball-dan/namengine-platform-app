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
    "family_context", "partner_alignment", "avoid", "notes"
  ];
  const orderIndex = new Map(questionOrder.map((id, index) => [id, index]));
  const questions = Array.from(form.querySelectorAll("[data-baby-question]"))
    .sort((left, right) => (orderIndex.get(left.dataset.questionId) ?? 99) - (orderIndex.get(right.dataset.questionId) ?? 99));
  const history = form.querySelector("[data-baby-answer-history]");
  const historyList = form.querySelector("[data-baby-answer-list]");
  const progressCopy = form.querySelector("[data-baby-progress-copy]");
  const progressBar = form.querySelector("[data-baby-progressbar]");
  const progressFill = form.querySelector("[data-baby-progress-fill]");
  const confirmation = form.querySelector("[data-baby-confirmation]");
  const completePanel = form.querySelector("[data-baby-complete]");
  const stage = form.querySelector("[data-baby-question-stage]");
  const skipped = new Set();
  let activeId = null;
  let transitionTimer = null;
  let completing = false;

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

  function isApplicable(question) {
    const dependency = question.dataset.conditionField;
    if (!dependency) return true;
    const source = questions.find((item) => item.dataset.questionId === dependency);
    return Boolean(source && valueFor(source) === question.dataset.conditionValue);
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
    }
    question.querySelectorAll("[data-choice-value]").forEach((button) => {
      button.classList.remove("is-selected");
      button.setAttribute("aria-checked", "false");
    });
    skipped.delete(question.dataset.questionId);
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
    progressCopy.textContent = `Question ${number} of ${total}`;
    progressBar.setAttribute("aria-valuenow", String(number));
    progressBar.setAttribute("aria-valuemax", String(total));
    progressFill.style.width = `${(number / total) * 100}%`;
  }

  function focusQuestion(question) {
    const target = question.querySelector("[data-choice-value].is-selected, [data-choice-value], textarea, input:not([type='hidden'])");
    if (target) target.focus({ preventScroll: true });
  }

  function showQuestion(question, options) {
    if (!question || completing) return;
    window.clearTimeout(transitionTimer);
    activeId = question.dataset.questionId;
    questions.forEach((item) => {
      const isActive = item === question;
      item.hidden = !isActive;
      item.classList.toggle("is-active", isActive);
    });
    stage.hidden = false;
    completePanel.hidden = true;
    renderHistory(question);
    updateProgress(question);
    if (options?.focus !== false) window.requestAnimationFrame(() => focusQuestion(question));
  }

  function nextQuestion(question) {
    syncConditions();
    const applicable = applicableQuestions();
    const index = applicable.indexOf(question);
    return applicable[index + 1] || null;
  }

  function confirmAndAdvance(question, label) {
    confirmation.textContent = label ? `Saved — ${label}` : "Saved";
    question.classList.add("is-confirmed");
    transitionTimer = window.setTimeout(() => {
      question.classList.remove("is-confirmed");
      confirmation.textContent = "";
      const next = nextQuestion(question);
      if (next) showQuestion(next);
      else finishInterview();
    }, motionQuery.matches ? 0 : 260);
  }

  function finishInterview() {
    completing = true;
    questions.forEach((question) => { question.hidden = true; });
    history.hidden = true;
    stage.hidden = true;
    progressCopy.textContent = "Interview complete";
    progressFill.style.width = "100%";
    progressBar.setAttribute("aria-valuenow", progressBar.getAttribute("aria-valuemax"));
    completePanel.hidden = false;
    window.setTimeout(() => HTMLFormElement.prototype.submit.call(form), motionQuery.matches ? 100 : loadingHandoff.delay);
  }

  function selectChoice(question, button) {
    const control = controlFor(question);
    const value = button.dataset.choiceValue;
    question.querySelectorAll("[data-choice-value]").forEach((choice) => {
      const selected = choice === button;
      choice.classList.toggle("is-selected", selected);
      choice.setAttribute("aria-checked", String(selected));
    });
    control.value = value;
    control.dispatchEvent(new Event("change", { bubbles: true }));
    skipped.delete(question.dataset.questionId);

    const otherWrap = question.querySelector("[data-baby-other-wrap]");
    const otherInput = question.querySelector("[data-other-input]");
    if (otherWrap) otherWrap.hidden = value !== "Other";
    if (otherInput) otherInput.disabled = value !== "Other";
    if (value === "Other" && otherInput) {
      otherInput.focus();
      return;
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
    const question = event.target.closest("[data-baby-question]");
    if (!question) return;
    if (event.target.closest("[data-baby-continue]")) continueText(question);
    if (event.target.closest("[data-baby-skip]")) {
      controlFor(question).value = "";
      skipped.add(question.dataset.questionId);
      confirmAndAdvance(question, "Skipped for now");
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
    form.scrollIntoView({ behavior: motionQuery.matches ? "auto" : "smooth", block: "start" });
  }
  begin?.addEventListener("click", (event) => {
    event.preventDefault();
    startInterview();
  });

  document.body.classList.add("baby-interview-enhanced");
  syncInitialSelections();
  syncConditions();
  if (form.dataset.editQuestion || window.location.hash === "#baby-intake-form") startInterview();
})();
