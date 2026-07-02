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

  forms.forEach((form) => {
    form.addEventListener("submit", () => {
      if (timer) {
        window.clearInterval(timer);
      }
      showProgress();
    });
  });
})();
