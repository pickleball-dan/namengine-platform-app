(function () {
  const legacyKey = "namengine.pet.tasteHistory.v1";
  const verticalSlug = getVerticalSlug();
  const verticalName = verticalSlug.charAt(0).toUpperCase() + verticalSlug.slice(1);
  const key = `namengine.${verticalSlug}.tasteHistory.v1`;

  function getVerticalSlug() {
    const marker = document.querySelector("[data-taste-vertical]");
    if (marker && marker.dataset.tasteVertical) {
      return marker.dataset.tasteVertical;
    }

    const session = document.querySelector("[data-taste-session-id]");
    const sessionId = session && session.dataset.tasteSessionId;
    if (sessionId && sessionId.includes("-")) {
      return sessionId.split("-")[0] || "pet";
    }
    return "pet";
  }

  function itemBelongsToVertical(item) {
    if (!item) return false;
    const prefix = `${verticalSlug}-`;
    return (
      String(item.sessionId || "").startsWith(prefix) ||
      String(item.listUrl || "").startsWith(`/${verticalSlug}`) ||
      String(item.shareUrl || "").includes(`/${verticalSlug}/`)
    );
  }

  function readStoredItems(storageKey) {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(storageKey) || "[]");
      return Array.isArray(parsed) ? parsed.map(normalizeItem).filter(Boolean) : [];
    } catch (error) {
      return [];
    }
  }

  function migrateLegacyHistory() {
    if (key === legacyKey || window.localStorage.getItem(key) !== null) {
      return [];
    }

    const migrated = readStoredItems(legacyKey).filter(itemBelongsToVertical);
    if (migrated.length) {
      writeHistory(migrated);
    }
    return migrated;
  }

  function readHistory() {
    const history = readStoredItems(key);
    return history.length ? history : migrateLegacyHistory();
  }

  function normalizeItem(item) {
    if (!item || typeof item !== "object") return null;
    if (item.sessionId) {
      return {
        sessionId: item.sessionId,
        title: item.title || `${verticalName} name search`,
        context: item.context || "Saved search",
        listUrl: item.listUrl || item.resumeUrl || `/${verticalSlug}`,
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
        listUrl: `/${verticalSlug}`,
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
      title: shell.dataset.tasteTitle || `${verticalName} name search`,
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
      listUrl: meta ? meta.listUrl : `/${verticalSlug}`,
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

  function clearLegacyVerticalHistory() {
    if (key === legacyKey) return;

    const remaining = readStoredItems(legacyKey).filter((item) => !itemBelongsToVertical(item));
    if (remaining.length) {
      window.localStorage.setItem(legacyKey, JSON.stringify(remaining.slice(0, 12)));
    } else {
      window.localStorage.removeItem(legacyKey);
    }
  }

  function clearHistory() {
    const confirmed = window.confirm(
      `Clear saved ${verticalName} loved names and searches from this browser?`
    );
    if (!confirmed) return;

    window.localStorage.setItem(key, "[]");
    clearLegacyVerticalHistory();
    render();

    const status = document.querySelector("[data-taste-history-status]");
    if (status) {
      status.textContent = "History cleared.";
    }
  }

  function render() {
    const history = readHistory();
    renderLovedSummary(history);
    renderDrawer(history);

    const clearButton = document.querySelector("[data-taste-history-clear]");
    if (clearButton) {
      clearButton.disabled = history.length === 0;
    }
  }

  function bindDialog() {
    const dialog = document.querySelector("[data-taste-history-dialog]");
    const openButton = document.querySelector("[data-taste-history-open]");
    const closeButton = document.querySelector("[data-taste-history-close]");
    const clearButton = document.querySelector("[data-taste-history-clear]");
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

    if (clearButton) {
      clearButton.addEventListener("click", clearHistory);
    }

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  }

  window.NamEngineTasteHistory = {
    add: addLovedName,
    render,
    clear: clearHistory,
    key,
  };
  window.NamEnginePetTasteHistory = window.NamEngineTasteHistory;

  upsertCurrentSession();
  bindDialog();
  render();
})();
