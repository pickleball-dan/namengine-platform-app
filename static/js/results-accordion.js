(function () {
  const shell = document.querySelector(".results-shell");
  if (!shell || shell.dataset.resultsAccordionInitialized === "true") return;

  const cards = Array.from(shell.querySelectorAll("[data-result-card]"));
  if (!cards.length) return;

  shell.dataset.resultsAccordionInitialized = "true";

  function setExpanded(card, expanded) {
    const toggle = card.querySelector("[data-result-card-toggle]");
    card.classList.toggle("is-expanded", expanded);
    if (toggle) toggle.setAttribute("aria-expanded", String(expanded));
  }

  shell.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-result-card-toggle]");
    if (!toggle) return;

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

  shell.classList.add("results-accordion-ready");
  cards.forEach((card) => setExpanded(card, false));
})();
