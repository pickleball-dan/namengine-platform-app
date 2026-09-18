(function () {
  const form = document.getElementById("boat-intake-form");
  if (!form) return;

  const questions = Array.from(form.querySelectorAll("[data-boat-question]"));
  const stage = form.querySelector("[data-boat-question-stage]");
  const progressbar = form.querySelector("[data-boat-progressbar]");
  const progressFill = form.querySelector("[data-boat-progress-fill]");
  const progressCopy = form.querySelector("[data-boat-progress-copy]");
  const review = form.querySelector("[data-boat-direction-review]");
  const reviewList = form.querySelector("[data-boat-direction-list]");
  const findButton = form.querySelector("[data-boat-direction-find]");
  const complete = form.querySelector("[data-boat-complete]");
  const nativeSubmit = form.querySelector(".boat-native-submit");
  let currentIndex = 0;

  if (!questions.length) return;

  function fieldFor(question) {
    return question.dataset.questionId ? form.elements[question.dataset.questionId] : null;
  }

  function fieldValue(question) {
    const field = fieldFor(question);
    return field ? String(field.value || "").trim() : "";
  }

  function setProgress() {
    const total = questions.length;
    const shown = Math.min(currentIndex + 1, total);
    const percent = total ? (shown / total) * 100 : 0;
    if (progressbar) {
      progressbar.setAttribute("aria-valuenow", String(shown));
      progressbar.setAttribute("aria-valuemax", String(total));
    }
    if (progressFill) progressFill.style.width = `${percent}%`;
    if (progressCopy) progressCopy.textContent = `Question ${shown} of ${total}`;
  }

  function showQuestion(index) {
    currentIndex = Math.max(0, Math.min(index, questions.length - 1));
    questions.forEach((question, idx) => {
      question.hidden = idx !== currentIndex;
    });
    if (stage) stage.hidden = false;
    if (review) review.hidden = true;
    if (complete) complete.hidden = true;
    setProgress();
    const active = questions[currentIndex];
    const back = active.querySelector("[data-boat-nav-back]");
    if (back) back.disabled = currentIndex === 0;
    const next = active.querySelector("[data-boat-next]");
    if (next) next.textContent = currentIndex === questions.length - 1 ? "Review direction" : "Next";
  }

  function canLeave(question) {
    if (question.dataset.required !== "true" || fieldValue(question)) {
      question.classList.remove("is-invalid");
      return true;
    }
    question.classList.add("is-invalid");
    const field = fieldFor(question);
    if (field && typeof field.focus === "function") field.focus({ preventScroll: false });
    return false;
  }

  function buildReview() {
    if (!reviewList) return;
    reviewList.innerHTML = "";
    questions.forEach((question, index) => {
      const row = document.createElement("div");
      row.className = "boat-direction-row";
      const dt = document.createElement("dt");
      dt.textContent = question.dataset.questionLabel || question.dataset.questionId || "Question";
      const dd = document.createElement("dd");
      dd.textContent = fieldValue(question) || "—";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.textContent = "Edit";
      edit.dataset.boatEditQuestion = String(index);
      row.append(dt, dd, edit);
      reviewList.append(row);
    });
  }

  function showReview() {
    buildReview();
    if (stage) stage.hidden = true;
    if (review) review.hidden = false;
    if (complete) complete.hidden = true;
    if (progressbar) progressbar.setAttribute("aria-valuenow", String(questions.length));
    if (progressFill) progressFill.style.width = "100%";
    if (progressCopy) progressCopy.textContent = "Review your direction";
  }

  form.addEventListener("click", (event) => {
    const choice = event.target.closest(".boat-choice-card[data-choice-value]");
    if (choice) {
      const question = choice.closest("[data-boat-question]");
      const field = fieldFor(question);
      if (!field) return;
      question.querySelectorAll(".boat-choice-card[data-choice-value]").forEach((button) => {
        const selected = button === choice;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-checked", String(selected));
      });
      field.value = choice.dataset.choiceValue || "";
      field.dispatchEvent(new Event("change", { bubbles: true }));
      question.classList.remove("is-invalid");
      return;
    }

    const back = event.target.closest("[data-boat-nav-back]");
    if (back) {
      showQuestion(currentIndex - 1);
      return;
    }

    const next = event.target.closest("[data-boat-next]");
    if (next) {
      const question = questions[currentIndex];
      if (!canLeave(question)) return;
      if (currentIndex === questions.length - 1) showReview();
      else showQuestion(currentIndex + 1);
      return;
    }

    const edit = event.target.closest("[data-boat-edit-question]");
    if (edit) showQuestion(Number(edit.dataset.boatEditQuestion || 0));
  });

  form.addEventListener("input", (event) => {
    const question = event.target.closest("[data-boat-question]");
    if (question && fieldValue(question)) question.classList.remove("is-invalid");
  });

  if (findButton) {
    findButton.addEventListener("click", () => {
      if (review) review.hidden = true;
      if (complete) complete.hidden = false;
      if (nativeSubmit && typeof form.requestSubmit === "function") form.requestSubmit(nativeSubmit);
      else form.submit();
    });
  }

  showQuestion(0);
})();
