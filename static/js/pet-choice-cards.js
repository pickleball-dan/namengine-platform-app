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
    if (active) other.focus({ preventScroll: true });
    else other.value = "";
  }

  function setSelectionSingle(group, button, control) {
    if (button.classList.contains("is-selected") && !control.required) {
      group.querySelectorAll("[data-choice-value]").forEach((c) => {
        c.classList.remove("is-selected");
        c.setAttribute("aria-checked", "false");
      });
      control.value = "";
      control.dispatchEvent(new Event("change", { bubbles: true }));
      syncOther(control);
      return;
    }
    group.querySelectorAll("[data-choice-value]").forEach((c) => {
      const sel = c === button;
      c.classList.toggle("is-selected", sel);
      c.setAttribute("aria-checked", String(sel));
    });
    control.value = button.dataset.choiceValue || "";
    control.dispatchEvent(new Event("change", { bubbles: true }));
    syncOther(control);
  }

  function setSelectionMulti(group, button, control, maxSelect) {
    const current = control.value ? control.value.split(",").filter(Boolean) : [];
    const val = button.dataset.choiceValue || "";
    const already = current.includes(val);
    let next;
    if (already) {
      next = current.filter((v) => v !== val);
    } else {
      if (current.length >= maxSelect) return;
      next = [...current, val];
    }
    control.value = next.join(",");
    group.querySelectorAll("[data-choice-value]").forEach((c) => {
      const sel = next.includes(c.dataset.choiceValue);
      c.classList.toggle("is-selected", sel);
      c.setAttribute("aria-checked", String(sel));
    });
    // update counter
    const counter = group.previousElementSibling;
    if (counter && counter.dataset.choiceCounter !== undefined) {
      counter.textContent = next.length >= maxSelect
        ? `${maxSelect} of ${maxSelect} selected`
        : `Choose up to ${maxSelect} — ${next.length} selected`;
    }
    control.dispatchEvent(new Event("change", { bubbles: true }));
  }

  groups.forEach((group) => {
    const controlId = group.dataset.choiceTarget;
    const control = controlId ? document.getElementById(controlId) : null;
    const maxSelect = parseInt(group.dataset.maxSelect || "1", 10);
    const isMulti = maxSelect > 1;

    if (control) syncOther(control);

    group.addEventListener("click", (event) => {
      const button = event.target.closest("[data-choice-value]");
      if (!button || !control) return;
      if (isMulti) {
        setSelectionMulti(group, button, control, maxSelect);
      } else {
        setSelectionSingle(group, button, control);
      }
    });

    group.addEventListener("keydown", (event) => {
      const button = event.target.closest("[data-choice-value]");
      if (!button || !["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(event.key)) return;
      event.preventDefault();
      const buttons = Array.from(group.querySelectorAll("[data-choice-value]"));
      const dir = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
      buttons[(buttons.indexOf(button) + dir + buttons.length) % buttons.length].focus();
    });
  });
})();
