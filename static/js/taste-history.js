(function () {
  const key = "namengine.pet.tasteHistory.v1";

  function readHistory() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(key) || "[]");
      return Array.isArray(parsed) ? parsed.map(normalizeItem).filter(Boolean) : [];
    } catch (error) {
      return [];
    }
  }

  function normalizeItem(item) {
    if (!item || typeof item !== "object") return null;
    if (item.sessionId) {
      return {
        sessionId: item.sessionId,
        title: item.title || "Pet name search",
        context: item.context || "Saved search",
        listUrl: item.listUrl || item.resumeUrl || "/pet",
        shareUrl: item.shareUrl || (item.sessionId ? `/share/${item.sessionId}` : ""),
        lovedNames: Array.isArray(item.lovedNames) ? item.lovedNames : [],
        savedAt: item.savedAt || new Date().toISOString(),
      };
    }

    if (item.name) {
      return {
        sessionId: `legacy-${item.name}`,
        title: "Loved names",
        context: item.context || "Loved name",
        listUrl: "/pet",
        shareUrl: "",
        lovedNames: [item.name],
        savedAt: item.savedAt || new Date().toISOString(),
      };
    }
    return null;
  }

  function writeHistory(history) {
    window.localStorage.setItem(key, JSON.stringify(history.slice(0, 12)));
  }

  function getCurrentSessionMeta() {
    const shell = document.querySelector("[data-taste-session-id]");
    if (!shell) return null;
    return {
      sessionId: shell.dataset.tasteSessionId,
      title: shell.dataset.tasteTitle || "Pet name search",
      context: shell.dataset.tasteContext || "Saved search",
      listUrl: shell.dataset.tasteListUrl || `${window.location.pathname}${window.location.search}`,
      shareUrl: shell.dataset.tasteShareUrl || `/share/${shell.dataset.tasteSessionId}`,
    };
  }

  function upsertCurrentSession() {
    const meta = getCurrentSessionMeta();
    if (!meta || !meta.sessionId) return null;

    const history = readHistory();
    const existing = history.find((item) => item.sessionId === meta.sessionId);
    const next = {
      ...meta,
      lovedNames: existing ? existing.lovedNames : [],
      savedAt: new Date().toISOString(),
    };
    const rest = history.filter((item) => item.sessionId !== meta.sessionId);
    writeHistory([next, ...rest]);
    render();
    return next;
  }

  function addLovedName(name, context) {
    if (!name) return;
    const meta = getCurrentSessionMeta();
    const history = readHistory();
    const sessionId = meta && meta.sessionId ? meta.sessionId : `loved-${name}`;
    const existing = history.find((item) => item.sessionId === sessionId);
    const lovedNames = existing ? existing.lovedNames.filter((item) => item !== name) : [];
    lovedNames.unshift(name);

    const next = {
      sessionId,
      title: meta ? meta.title : "Loved names",
      context: meta ? meta.context : context || "Loved name",
      listUrl: meta ? meta.listUrl : "/pet",
      shareUrl: meta ? meta.shareUrl : "",
      lovedNames,
      savedAt: new Date().toISOString(),
    };
    const rest = history.filter((item) => item.sessionId !== sessionId);
    writeHistory([next, ...rest]);
    render();
  }

  function renderLovedSummary(history) {
    const list = document.querySelector("[data-taste-history-list]");
    if (!list) return;

    const lovedNames = history.flatMap((item) => item.lovedNames || []).slice(0, 5);
    list.innerHTML = "";
    if (!lovedNames.length) {
      const empty = document.createElement("li");
      empty.textContent = "No loved names yet.";
      list.appendChild(empty);
      return;
    }

    lovedNames.forEach((name) => {
      const li = document.createElement("li");
      const strong = document.createElement("strong");
      const span = document.createElement("span");
      strong.textContent = name;
      span.textContent = "Loved name";
      li.append(strong, span);
      list.appendChild(li);
    });
  }

  function renderDrawer(history) {
    const list = document.querySelector("[data-taste-history-drawer-list]");
    if (!list) return;

    list.innerHTML = "";
    if (!history.length) {
      const empty = document.createElement("li");
      empty.textContent = "No saved taste history yet.";
      list.appendChild(empty);
      return;
    }

    history.forEach((item) => {
      const li = document.createElement("li");
      const title = document.createElement("strong");
      const context = document.createElement("span");
      const loved = document.createElement("p");
      const actions = document.createElement("div");
      const resume = document.createElement("a");
      const view = document.createElement("a");

      title.textContent = item.title;
      context.textContent = item.context;
      loved.textContent = item.lovedNames.length
        ? `Loved: ${item.lovedNames.join(", ")}`
        : "No loved names saved for this list yet.";
      actions.className = "taste-history-actions";
      resume.className = "button-link";
      resume.href = item.listUrl;
      resume.textContent = "Resume";
      view.className = "button-link secondary-button";
      view.href = item.shareUrl || item.listUrl;
      view.textContent = "View list";

      actions.append(resume, view);
      li.append(title, context, loved, actions);
      list.appendChild(li);
    });
  }

  function render() {
    const history = readHistory();
    renderLovedSummary(history);
    renderDrawer(history);
  }

  function bindDialog() {
    const dialog = document.querySelector("[data-taste-history-dialog]");
    const openButton = document.querySelector("[data-taste-history-open]");
    const closeButton = document.querySelector("[data-taste-history-close]");
    if (!dialog || !openButton) return;

    openButton.addEventListener("click", () => {
      render();
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
    });

    if (closeButton) {
      closeButton.addEventListener("click", () => dialog.close());
    }

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  }

  window.NamEnginePetTasteHistory = {
    add: addLovedName,
    render,
  };

  upsertCurrentSession();
  bindDialog();
  render();
})();
