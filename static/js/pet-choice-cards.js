(function () {
  const groups = Array.from(document.querySelectorAll("[data-choice-card-list]"));
  if (!groups.length) return;

  function syncOther(control) {
    if (!control || !control.dataset.otherSelect) return;
    const other = document.getElementById(control.dataset.otherSelect);
    if (!other) return;
    const active = control.value === "Other";
    other.hidden = !active;
    other.disabled = !active;
    if (active) {
      other.focus({ preventScroll: true });
    } else {
      other.value = "";
    }
  }

  function setSelection(group, button) {
    const controlId = group.dataset.choiceTarget;
    const control = controlId ? document.getElementById(controlId) : null;
    if (!control) return;

    group.querySelectorAll("[data-choice-value]").forEach((choice) => {
      const selected = choice === button;
      choice.classList.toggle("is-selected", selected);
      choice.setAttribute("aria-checked", String(selected));
    });
    control.value = button.dataset.choiceValue || "";
    control.dispatchEvent(new Event("change", { bubbles: true }));
    syncOther(control);
  }

  groups.forEach((group) => {
    const controlId = group.dataset.choiceTarget;
    const control = controlId ? document.getElementById(controlId) : null;
    if (control) {
      syncOther(control);
    }

    group.addEventListener("click", (event) => {
      const button = event.target.closest("[data-choice-value]");
      if (button) setSelection(group, button);
    });

    group.addEventListener("keydown", (event) => {
      const button = event.target.closest("[data-choice-value]");
      if (!button || !["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(event.key)) return;
      event.preventDefault();
      const buttons = Array.from(group.querySelectorAll("[data-choice-value]"));
      const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
      buttons[(buttons.indexOf(button) + direction + buttons.length) % buttons.length].focus();
    });
  });
})();
