(function () {
  "use strict";

  const bodyClass = document.body.className;
  const slugMatch = bodyClass.match(/vertical-([a-z]+)/);
  const slug = slugMatch ? slugMatch[1] : null;
  if (!slug || !["pet", "business"].includes(slug)) return;

  const p = slug;
  const form = document.querySelector("form[data-progress-form]");
  const reviewSection = document.querySelector("[data-" + p + "-direction-review]");
  const directionList = document.querySelector("[data-" + p + "-direction-list]");
  const findBtn = document.querySelector("[data-" + p + "-direction-find]");
  const nativeSubmit = form ? form.querySelector("button[type=submit]") : null;

  if (!form || !reviewSection || !directionList || !findBtn || !nativeSubmit) return;

  function getFieldValue(label) {
    // Choice card: read the selected card's data-choice-value
    const choiceList = label.querySelector("[data-choice-card-list]");
    if (choiceList) {
      const selected = choiceList.querySelector("[aria-checked='true']");
      if (selected) {
        const val = selected.dataset.choiceValue || "";
        if (val === "Other") {
          const targetId = choiceList.dataset.choiceTarget;
          const otherId = targetId ? targetId + "_other" : null;
          const other = otherId ? document.getElementById(otherId) : null;
          return other ? other.value.trim() : "";
        }
        return val.trim();
      }
      return "";
    }
    // Standard input / textarea / select
    const input = label.querySelector("input:not([type=hidden]), textarea, select");
    return input ? input.value.trim() : "";
  }

  function getLabelText(label) {
    const copy = label.querySelector(".field-label-copy");
    if (!copy) return "";
    const clone = copy.cloneNode(true);
    const anchor = clone.querySelector(".baby-field-anchor");
    if (anchor) anchor.remove();
    return clone.textContent.trim();
  }

  function buildRows() {
    directionList.replaceChildren();
    const labels = form.querySelectorAll("label.field");
    labels.forEach(function (label) {
      const labelText = getLabelText(label);
      if (!labelText) return;
      const value = getFieldValue(label);

      const row = document.createElement("div");
      row.className = p + "-direction-row";

      const dt = document.createElement("dt");
      dt.textContent = labelText;

      const dd = document.createElement("dd");
      if (!value) dd.className = "is-empty";
      dd.textContent = value || "Not answered";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.textContent = "Edit";
      editBtn.addEventListener("click", function () {
        hideReview();
        label.scrollIntoView({ behavior: "smooth", block: "center" });
        const focusTarget = label.querySelector("input:not([aria-hidden='true']):not([type=hidden]), textarea, select");
        if (focusTarget) focusTarget.focus();
      });

      row.appendChild(dt);
      row.appendChild(dd);
      row.appendChild(editBtn);
      directionList.appendChild(row);
    });
  }

  function showReview() {
    buildRows();
    nativeSubmit.hidden = true;
    reviewSection.hidden = false;
    reviewSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function hideReview() {
    reviewSection.hidden = true;
    nativeSubmit.hidden = false;
  }

  // Auto-submit when last choice card group gets a selection
  const allChoiceLists = Array.from(form.querySelectorAll("[data-choice-card-list]"));
  const lastChoiceList = allChoiceLists[allChoiceLists.length - 1];
  if (lastChoiceList) {
    lastChoiceList.addEventListener("click", function (e) {
      const card = e.target.closest("[data-choice-value]");
      if (!card) return;
      // Small delay so pet-choice-cards.js sets aria-checked first
      setTimeout(function () {
        form.requestSubmit ? form.requestSubmit() : form.submit();
      }, 150);
    });
  }

  // Also keep manual submit working (in case they tab/keyboard)
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    e.stopImmediatePropagation();
  }, true);

  // "Generate" button — submit the form
  findBtn.addEventListener("click", function () {
    form.requestSubmit ? form.requestSubmit() : form.submit();
  });

})();
