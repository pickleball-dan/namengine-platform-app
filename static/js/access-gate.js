(function () {
  const shell = document.querySelector("[data-access-gate-url]");
  if (!shell) return;

  const accessUrl = shell.dataset.accessGateUrl;
  const modalTitle = shell.dataset.accessGateTitle || "Unlock this list";
  const modalBody = shell.dataset.accessGateBody || "Unlock Full Access to explore, react, compare, choose, share, and generate refined rounds.";
  let modal = null;
  let priorFocus = null;

  function buildModal() {
    const element = document.createElement("div");
    element.className = "access-gate-modal-backdrop";
    element.hidden = true;
    element.innerHTML = `
      <section class="access-gate-modal" role="dialog" aria-modal="true" aria-labelledby="access-gate-title" aria-describedby="access-gate-body">
        <button class="access-gate-close" type="button" data-access-gate-close aria-label="Close unlock message">×</button>
        <p class="eyebrow">NamEngine Access</p>
        <h2 id="access-gate-title"></h2>
        <p id="access-gate-body"></p>
        <ul class="access-gate-list">
          <li>Explore every name in detail</li>
          <li>React, save, compare, choose, and share</li>
          <li>Generate refined rounds shaped by your taste</li>
        </ul>
        <div class="access-gate-actions">
          <a class="button-link access-gate-primary" data-access-gate-unlock>Unlock Access</a>
          <button class="button-link secondary-button access-gate-secondary" type="button" data-access-gate-close>Keep browsing the preview</button>
        </div>
        <div class="access-gate-payments">
          <span>Secured by Stripe</span>
          <span class="access-gate-payment-cards">Visa &middot; Mastercard &middot; Amex &middot; Apple Pay &middot; Google Pay</span>
        </div>
      </section>
    `;
    element.querySelector("#access-gate-title").textContent = modalTitle;
    element.querySelector("#access-gate-body").textContent = modalBody;
    element.querySelector("[data-access-gate-unlock]").setAttribute("href", accessUrl);
    element.addEventListener("click", (event) => {
      if (event.target === element || event.target.closest("[data-access-gate-close]")) {
        closeModal();
      }
    });
    document.body.appendChild(element);
    return element;
  }

  function openModal(trigger) {
    priorFocus = trigger || document.activeElement;
    modal = modal || buildModal();
    modal.hidden = false;
    document.body.classList.add("access-gate-open");
    modal.querySelector("[data-access-gate-unlock]")?.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("access-gate-open");
    if (priorFocus && typeof priorFocus.focus === "function") {
      priorFocus.focus();
    }
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-premium-action]");
    if (!trigger) return;
    event.preventDefault();
    event.stopPropagation();
    openModal(trigger);
  }, true);
})();

// Save-progress form handler
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('[data-save-progress-form]');
  if (!form) return;

  const statusEl = form.querySelector('.save-progress-status');
  const submitBtn = form.querySelector('.save-progress-submit');
  const defaultSubmitText = submitBtn ? submitBtn.textContent : 'Send My Link';

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const email = form.querySelector('[name="email"]').value.trim();
    const sessionId = form.querySelector('[name="session_id"]').value.trim();
    if (!email) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending…';
    statusEl.textContent = '';
    statusEl.className = 'save-progress-status';

    try {
      const res = await fetch('/api/save-progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, session_id: sessionId }),
      });
      const data = await res.json();
      if (res.ok) {
        statusEl.textContent = '✓ Check your email — your link is on its way.';
        statusEl.className = 'save-progress-status is-success';
        submitBtn.textContent = 'Sent!';
      } else {
        statusEl.textContent = 'Something went wrong. Try again.';
        statusEl.className = 'save-progress-status is-error';
        submitBtn.disabled = false;
        submitBtn.textContent = defaultSubmitText;
      }
    } catch (err) {
      statusEl.textContent = 'Could not connect. Try again.';
      statusEl.className = 'save-progress-status is-error';
      submitBtn.disabled = false;
      submitBtn.textContent = defaultSubmitText;
    }
  });
});
