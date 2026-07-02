(function () {
  const overlay = document.querySelector("[data-progress-overlay]");
  const current = document.querySelector("[data-progress-current]");
  const steps = Array.from(document.querySelectorAll("[data-progress-step]"));
  const forms = Array.from(document.querySelectorAll("[data-progress-form]"));

  if (!overlay || !current || !steps.length || !forms.length) {
    return;
  }

  let timer = null;

  function activateStep(index) {
    steps.forEach((step, stepIndex) => {
      step.classList.toggle("is-active", stepIndex === index);
      step.classList.toggle("is-complete", stepIndex < index);
    });
    current.textContent = steps[index].textContent;
  }

  function showProgress() {
    overlay.hidden = false;
    activateStep(0);
    let index = 0;
    timer = window.setInterval(() => {
      index = Math.min(index + 1, steps.length - 1);
      activateStep(index);
      if (index === steps.length - 1) {
        window.clearInterval(timer);
      }
    }, 750);
  }

  function fieldForControl(control) {
    return control.closest(".field");
  }

  function clearInvalidField(control) {
    const field = fieldForControl(control);
    if (!field) return;

    field.classList.remove("is-required-missing");
    control.removeAttribute("aria-invalid");
    const error = field.querySelector(".field-error");
    if (error) {
      error.remove();
    }
  }

  function markInvalidField(control) {
    const field = fieldForControl(control);
    if (!field) return;

    field.classList.add("is-required-missing");
    control.setAttribute("aria-invalid", "true");

    let error = field.querySelector(".field-error");
    if (!error) {
      error = document.createElement("small");
      error.className = "field-error";
      field.appendChild(error);
    }
    error.textContent = "Required before we can generate names.";
  }

  function focusFirstInvalid(form) {
    const controls = Array.from(form.querySelectorAll("input, select, textarea"));
    const invalidControl = controls.find((control) => !control.checkValidity());
    if (!invalidControl) return false;

    controls.forEach((control) => {
      if (control.checkValidity()) {
        clearInvalidField(control);
      }
    });
    markInvalidField(invalidControl);
    fieldForControl(invalidControl)?.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => invalidControl.focus({ preventScroll: true }), 220);
    return true;
  }

  forms.forEach((form) => {
    form.addEventListener("input", (event) => {
      if (event.target.matches("input, select, textarea") && event.target.checkValidity()) {
        clearInvalidField(event.target);
      }
    });

    form.addEventListener("change", (event) => {
      if (event.target.matches("input, select, textarea") && event.target.checkValidity()) {
        clearInvalidField(event.target);
      }
    });

    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        focusFirstInvalid(form);
        return;
      }
      if (timer) {
        window.clearInterval(timer);
      }
      showProgress();
    });
  });
})();
