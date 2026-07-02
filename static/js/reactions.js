(function () {
  const shell = document.querySelector("[data-session-id]");
  if (!shell) return;

  const sessionId = shell.dataset.sessionId;

  async function sendReaction(row, button) {
    const resultId = row.dataset.resultId;
    const value = button.dataset.reactionValue;
    const status = row.parentElement.querySelector(".reaction-status");

    row.querySelectorAll("button").forEach((item) => {
      item.classList.remove("is-selected");
      item.disabled = true;
    });
    button.classList.add("is-selected");
    if (status) status.textContent = "Saved";

    try {
      const response = await fetch("/api/react", {
        method: "POST",
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
      if (
        value === "love" &&
        window.NamEnginePetTasteHistory &&
        typeof window.NamEnginePetTasteHistory.add === "function"
      ) {
        window.NamEnginePetTasteHistory.add(button.dataset.resultName, "Loved from results");
      }
      if (status) {
        const counts = data.reaction_counts;
        if (counts) {
          status.textContent = `Saved: ${button.textContent} · ${counts.love} loved`;
        } else {
          status.textContent = `Saved: ${button.textContent}`;
        }
      }
    } catch (error) {
      button.classList.remove("is-selected");
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
