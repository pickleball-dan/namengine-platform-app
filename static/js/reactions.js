(function () {
  const shell = document.querySelector("[data-session-id]");
  if (!shell) return;

  const sessionId = shell.dataset.sessionId;
  const refineForm = document.querySelector("[data-min-reactions]");
  const refineButton = refineForm ? refineForm.querySelector("[data-refine-submit]") : null;
  const refineGate = refineForm ? refineForm.querySelector("[data-refine-reaction-gate]") : null;
  const savedCount = document.querySelector("[data-saved-count]");

  function updateSavedCount(counts) {
    if (!savedCount || !counts) return;
    const loved = Number(counts.love || 0);
    savedCount.textContent = `Saved ${loved} ${loved === 1 ? "name" : "names"}`;
  }

  function updateRefineGate(counts) {
    if (!refineForm || !counts) return;

    const minimum = Number(refineForm.dataset.minReactions || 3);
    // Legacy maybe rows can still be returned for an older session. Count them
    // toward its established refinement threshold without exposing a new Maybe
    // control. New public submissions are Love or No only.
    const total = Number(counts.love || 0) + Number(counts.maybe || 0) + Number(counts.no || 0);
    const remaining = Math.max(minimum - total, 0);

    refineForm.dataset.reactionTotal = String(total);
    if (refineButton) {
      refineButton.disabled = remaining > 0;
    }
    if (refineGate) {
      refineGate.classList.remove("is-error");
      refineGate.textContent = remaining > 0
        ? `React to ${remaining} more ${remaining === 1 ? "name" : "names"} before generating the next list.`
        : "Ready to generate the next list.";
    }
  }

  async function sendReaction(row, button) {
    const resultId = row.dataset.resultId;
    const value = button.dataset.reactionValue;
    const label = button.dataset.reactionLabel || value;
    const status = row.parentElement.querySelector(".reaction-status");

    const previousValue = row.querySelector("button.is-selected")?.dataset.reactionValue || "";
    row.querySelectorAll("button").forEach((item) => {
      item.classList.remove("is-selected");
      item.setAttribute("aria-pressed", "false");
      item.disabled = true;
    });
    button.classList.add("is-selected");
    button.setAttribute("aria-pressed", "true");
    if (status) status.textContent = "Saving…";

    try {
      const response = await fetch("/api/react", {
        method: "POST",
        keepalive: true,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          result_id: resultId,
          value,
        }),
      });

      if (!response.ok) {
        throw new Error("reaction failed");
      }

      const data = await response.json();
      const tasteHistory = window.NamEngineTasteHistory || window.NamEnginePetTasteHistory;
      if (
        value === "love" &&
        tasteHistory &&
        typeof tasteHistory.add === "function"
      ) {
        tasteHistory.add(button.dataset.resultName, "Loved from results");
      }
      if (status) {
        const counts = data.reaction_counts;
        if (counts) {
          status.textContent = `Saved: ${label} · ${counts.love} loved`;
          updateSavedCount(counts);
          updateRefineGate(counts);
        } else {
          status.textContent = `Saved: ${label}`;
        }
      }
    } catch (error) {
      button.classList.remove("is-selected");
      button.setAttribute("aria-pressed", "false");
      if (previousValue) {
        const previous = row.querySelector(`[data-reaction-value="${previousValue}"]`);
        previous?.classList.add("is-selected");
        previous?.setAttribute("aria-pressed", "true");
      }
      if (status) status.textContent = "Could not save";
    } finally {
      row.querySelectorAll("button").forEach((item) => {
        item.disabled = false;
      });
    }
  }

  document.querySelectorAll(".reaction-row").forEach((row) => {
    row.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-reaction-value]");
      if (!button) return;
      sendReaction(row, button);
    });
  });
})();
