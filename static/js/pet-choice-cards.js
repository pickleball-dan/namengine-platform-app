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

  function updateCounter(group, selected, maxSelect) {
    const counter = group.closest("[data-pet-question], [data-boat-question], label, fieldset")
      ?.querySelector("[data-pet-choice-counter]");
    if (!counter) return;
    const remaining = maxSelect - selected;
    if (remaining <= 0) {
      counter.textContent = `${maxSelect} selected`;
    } else {
      counter.textContent = `Choose up to ${maxSelect} — ${selected} selected`;
    }
  }

  function setSelectionMulti(group, button, control, maxSelect) {
    const currentValues = control.value ? control.value.split(",").filter(Boolean) : [];
    const value = button.dataset.choiceValue || "";
    const alreadySelected = currentValues.includes(value);

    let newValues;
    if (alreadySelected) {
      // Deselect
      newValues = currentValues.filter((v) => v !== value);
    } else {
      // Select — enforce max
      if (currentValues.length >= maxSelect) return;
      newValues = [...currentValues, value];
    }

    control.value = newValues.join(",");

    group.querySelectorAll("[data-choice-value]").forEach((card) => {
      const sel = newValues.includes(card.dataset.choiceValue);
      card.classList.toggle("is-selected", sel);
      card.setAttribute("aria-checked", String(sel));
      // Dim unavailable choices when at max
      if (newValues.length >= maxSelect && !sel) {
        card.classList.add("is-dimmed");
      } else {
        card.classList.remove("is-dimmed");
      }
    });

    updateCounter(group, newValues.length, maxSelect);
    control.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setSelectionSingle(group, button, control) {
    // Toggle: clicking an already-selected card on an optional question deselects it.
    if (button.classList.contains("is-selected") && !control.required) {
      group.querySelectorAll("[data-choice-value]").forEach((choice) => {
        choice.classList.remove("is-selected");
        choice.setAttribute("aria-checked", "false");
      });
      control.value = "";
      control.dispatchEvent(new Event("change", { bubbles: true }));
      syncOther(control);
      return;
    }

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
    const maxSelect = parseInt(group.dataset.maxSelect || "1", 10);
    const isMulti = maxSelect > 1;

    if (control) {
      syncOther(control);
      if (isMulti) {
        // Sync initial state for multi-select
        const currentValues = control.value ? control.value.split(",").filter(Boolean) : [];
        updateCounter(group, currentValues.length, maxSelect);
      }
    }

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
      const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
      buttons[(buttons.indexOf(button) + direction + buttons.length) % buttons.length].focus();
    });
  });
})();
