(function () {
  const overlay = document.querySelector("[data-progress-overlay]");
  const current = document.querySelector("[data-progress-current]");
  const eyebrow = document.querySelector("[data-progress-eyebrow]");
  const visual = document.querySelector("[data-progress-visual]");
  const visualLabel = document.querySelector(".progress-visual-label");
  const note = document.querySelector("[data-progress-note]");
  const steps = Array.from(document.querySelectorAll("[data-progress-step]"));
  const forms = Array.from(document.querySelectorAll("form"));
  const minimumProgressMs = 18000;
  const defaultLongWaitMessages = [
    "Working hard to get your perfect matches.",
    "Exploring meaning, sound, and cultural fit.",
    "Comparing the strongest names against your taste.",
    "Almost there — shaping the final shortlist."
  ];
  const babyLongWaitMessages = [
    "Interpreting your naming taste…",
    "Building a broader candidate pool…",
    "Comparing names against your story and style…",
    "Rejecting weaker fits before we show you finalists…",
    "Shaping the shortlist — quality matters more than speed…",
    "Still working. We’re keeping the page here while NamEngine thinks…"
  ];
  const petLongWaitMessages = [
    "Getting to know their personality...",
    "Listening for names that are joyful to call...",
    "Balancing affection, energy, and everyday fit...",
    "Finding names that feel unmistakably like them..."
  ];
  const businessLongWaitMessages = [
    "Reading the market and positioning signals...",
    "Testing clarity, credibility, and distinctiveness...",
    "Considering audience fit and launch practicality...",
    "Building the strongest strategic shortlist..."
  ];
  let longWaitMessages = defaultLongWaitMessages;

  if (!forms.length) {
    return;
  }

  const canShowProgress = Boolean(overlay && current && steps.length);

  let timer = null;
  let patienceTimer = null;
  let submittingForm = null;

  function cleanValue(value) {
    return String(value || "").trim();
  }

  function formValue(form, names) {
    const fields = Array.isArray(names) ? names : [names];
    for (const name of fields) {
      const control = form.elements.namedItem(name);
      const value = cleanValue(control && control.value);
      if (value) {
        return value;
      }
    }
    return "";
  }

  function subjectFor(form) {
    const petType = formValue(form, ["pet_type", "species"]);
    if (petType) {
      return `this ${petType.toLowerCase()}`;
    }
    if (formValue(form, "business_description")) {
      return "this brand";
    }
    if (formValue(form, ["genre", "role", "tone"])) {
      return "this character";
    }
    if (formValue(form, ["gender", "family_context"])) {
      return "this baby name";
    }
    return "this identity";
  }

  function personalizeProgress(form) {
    const subject = subjectFor(form);
    const vibe = formValue(form, ["vibe", "style", "tone"]);
    const culture = formValue(form, "cultural_heritage");
    const isBaby = subject === "this baby name";
    const isPet = Boolean(formValue(form, ["pet_type", "species"]));
    const isBusiness = Boolean(formValue(form, "business_description"));
    longWaitMessages = isBaby
      ? babyLongWaitMessages
      : isPet
        ? petLongWaitMessages
        : isBusiness
          ? businessLongWaitMessages
          : defaultLongWaitMessages;
    const feelLine = vibe ? `Matching the ${vibe.toLowerCase()} feel` : "Matching the feel";
    const cultureLine = culture && culture !== "No preference"
      ? `Exploring ${culture.toLowerCase()} meaning and sound`
      : "Exploring meaning and sound";
    const labels = isBaby ? [
      "Bringing together everything you shared",
      cultureLine,
      "Exploring names that fit your style",
      "Looking at sound, meaning, and feeling",
      "Finding names worth considering",
    ] : isPet ? [
      "Getting to know their personality",
      "Listening for names that are joyful to call",
      feelLine,
      "Checking sound and everyday fit",
      "Finding names that feel like them",
    ] : isBusiness ? [
      "Reading your business brief",
      "Mapping the audience and category",
      feelLine,
      "Checking credibility and launch fit",
      "Building the strategic shortlist",
    ] : [
      "Reading the details",
      `Finding names for ${subject}`,
      feelLine,
      "Checking sound and use",
      "Picking the strongest names",
    ];

    if (eyebrow) {
      eyebrow.textContent = isBaby
        ? "A thoughtful first look"
        : isPet
          ? "Finding names that feel like them"
          : isBusiness
            ? "Building your strategic brand shortlist"
            : `Building a shortlist for ${subject}`;
    }
    if (visualLabel && isBaby) {
      visualLabel.textContent = "Family fit";
    }
    if (note) {
      note.textContent = isBaby
        ? "We’re listening to your story, style, and the feeling you want a name to carry."
        : isPet
          ? "We’re matching personality, sound, affection, and everyday callability."
          : isBusiness
            ? "We’re weighing positioning, audience, distinctiveness, and practical launch fit."
            : "A few quick checks before the list appears.";
    }
    steps.forEach((step, index) => {
      const label = labels[index] || cleanValue(step.dataset.progressHeadline || step.textContent);
      step.textContent = label;
      step.dataset.progressHeadline = label;
    });
  }

  function activateStep(index) {
    steps.forEach((step, stepIndex) => {
      step.classList.toggle("is-active", stepIndex === index);
      step.classList.toggle("is-complete", stepIndex < index);
    });
    current.textContent = steps[index].dataset.progressHeadline || steps[index].textContent;
    if (visual) {
      visual.classList.remove("is-pulsing");
      void visual.offsetWidth;
      visual.classList.add("is-pulsing");
    }
  }

  function showProgress() {
    if (!canShowProgress) return;
    overlay.hidden = false;
    if (visual) {
      visual.classList.add("is-searching");
    }
    activateStep(0);
    let index = 0;
    timer = window.setInterval(() => {
      index = Math.min(index + 1, steps.length - 1);
      activateStep(index);
      if (index === steps.length - 1) {
        window.clearInterval(timer);
      }
    }, Math.max(900, Math.floor(minimumProgressMs / steps.length)));

    let patienceIndex = 0;
    patienceTimer = window.setInterval(() => {
      if (!current) return;
      current.textContent = longWaitMessages[patienceIndex % longWaitMessages.length];
      patienceIndex += 1;
      if (visual) {
        visual.classList.remove("is-pulsing");
        void visual.offsetWidth;
        visual.classList.add("is-pulsing");
      }
    }, 6500);
  }

  window.addEventListener("namengine:progress-step", (event) => {
    const requestedStep = Number(event.detail && event.detail.index);
    if (Number.isInteger(requestedStep)) {
      activateStep(Math.max(0, Math.min(requestedStep, steps.length - 1)));
    }
  });

  function requestForForm(form, submitter) {
    const method = (form.method || "get").toUpperCase();
    const action = form.action || window.location.href;
    const formData = new FormData(form);

    if (submitter && submitter.name) {
      formData.append(submitter.name, submitter.value);
    }

    if (method === "GET") {
      const url = new URL(action, window.location.href);
      const params = new URLSearchParams(formData);
      url.search = params.toString();
      return {
        navigateUrl: url.toString(),
        request: fetch(url, {
          method: "GET",
          credentials: "same-origin",
          headers: { "Accept": "text/html" },
        }),
      };
    }

    return {
      navigateUrl: action,
      request: fetch(action, {
        method,
        body: formData,
        credentials: "same-origin",
        headers: {
          "Accept": "text/html",
          "X-NamEngine-Progress": "1",
        },
      }),
    };
  }

  function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function syncOtherSelect(select) {
    const input = document.getElementById(select.dataset.otherSelect);
    if (!input) return;

    const isOther = select.value === "Other";
    input.hidden = !isOther;
    input.disabled = !isOther;
    input.required = isOther && select.required;
    if (!isOther) {
      input.value = "";
      clearInvalidField(input);
    }
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
    error.textContent = document.body.classList.contains("vertical-baby")
      ? "Please answer this before we continue."
      : "Required before we can generate names.";
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
    form.querySelectorAll("select[data-other-select]").forEach((select) => {
      syncOtherSelect(select);
      select.addEventListener("change", () => syncOtherSelect(select));
    });

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
      if (submittingForm === form) {
        return;
      }
      if (!form.checkValidity()) {
        event.preventDefault();
        focusFirstInvalid(form);
        return;
      }
      if (!form.matches("[data-progress-form]") || !canShowProgress) {
        return;
      }

      event.preventDefault();
      if (timer) {
        window.clearInterval(timer);
      }
      if (patienceTimer) {
        window.clearInterval(patienceTimer);
      }
      personalizeProgress(form);
      showProgress();
      submittingForm = form;

      const { navigateUrl, request } = requestForForm(form, event.submitter);
      const minimumWait = wait(minimumProgressMs);

      Promise.all([request, minimumWait])
        .then(([response]) => {
          if (!response.ok) {
            throw new Error(`Progress request failed: ${response.status}`);
          }
          window.location.assign(response.url || navigateUrl);
        })
        .catch(() => {
          minimumWait.then(() => {
            HTMLFormElement.prototype.submit.call(form);
          });
        });
    });
  });
})();
