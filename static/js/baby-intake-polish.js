(function () {
  const form = document.querySelector(".baby-intake-form");
  if (!form) return;

  const sections = Array.from(form.querySelectorAll("[data-baby-intake-section]"));
  const submitButton = form.querySelector('button[type="submit"]');
  let priming = false;

  function sectionIsComplete(section) {
    const required = Array.from(section.querySelectorAll("input[required], select[required], textarea[required]"));
    return required.length > 0 && required.every((control) => control.checkValidity());
  }

  function updateSections() {
    sections.forEach((section) => {
      section.classList.toggle("is-complete", sectionIsComplete(section));
    });
  }

  form.addEventListener("input", updateSections);
  form.addEventListener("change", updateSections);
  updateSections();

  form.addEventListener("submit", (event) => {
    if (priming || !form.checkValidity() || !submitButton) return;

    event.preventDefault();
    priming = true;
    submitButton.disabled = true;
    submitButton.classList.add("is-priming");
    const vertical = form.id.split("-")[0];
    submitButton.textContent = vertical === "business"
      ? "✦ Building your brand profile..."
      : vertical === "pet"
        ? "✦ Building their naming profile..."
        : "✦ Building your naming profile...";

    window.setTimeout(() => {
      HTMLFormElement.prototype.submit.call(form);
    }, 650);
  });
})();
