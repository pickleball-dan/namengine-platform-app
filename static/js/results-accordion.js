(function () {
  const shell = document.querySelector(".results-shell");
  if (!shell || shell.dataset.resultsAccordionInitialized === "true") return;

  const mobileQuery = window.matchMedia("(max-width: 760px)");
  const cards = Array.from(shell.querySelectorAll("[data-result-card]"));
  if (!cards.length) return;

  shell.dataset.resultsAccordionInitialized = "true";

  function setExpanded(card, expanded) {
    const toggle = card.querySelector("[data-result-card-toggle]");
    const label = card.querySelector("[data-result-card-toggle-label]");
    card.classList.toggle("is-expanded", expanded);
    if (toggle) toggle.setAttribute("aria-expanded", String(expanded));
    if (label) label.textContent = expanded ? "Hide details" : "View details";
  }

  function applyViewportMode() {
    if (mobileQuery.matches) {
      shell.classList.add("results-accordion-ready");
      cards.forEach((card) => setExpanded(card, false));
      return;
    }

    shell.classList.remove("results-accordion-ready");
    cards.forEach((card) => setExpanded(card, true));
  }

  shell.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-result-card-toggle]");
    if (!toggle || !mobileQuery.matches) return;

    const card = toggle.closest("[data-result-card]");
    if (!card) return;
    const opening = toggle.getAttribute("aria-expanded") !== "true";

    if (opening) {
      cards.forEach((otherCard) => {
        if (otherCard !== card) setExpanded(otherCard, false);
      });
    }
    setExpanded(card, opening);
  });

  if (typeof mobileQuery.addEventListener === "function") {
    mobileQuery.addEventListener("change", applyViewportMode);
  } else {
    mobileQuery.addListener(applyViewportMode);
  }
  applyViewportMode();
})();
