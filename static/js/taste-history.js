(function () {
  const key = "namengine.pet.tasteHistory.v1";

  function readHistory() {
    try {
      return JSON.parse(window.localStorage.getItem(key) || "[]");
    } catch (error) {
      return [];
    }
  }

  function writeHistory(history) {
    window.localStorage.setItem(key, JSON.stringify(history.slice(0, 12)));
  }

  function render() {
    const list = document.querySelector("[data-taste-history-list]");
    if (!list) return;

    const history = readHistory();
    list.innerHTML = "";
    if (!history.length) {
      const empty = document.createElement("li");
      empty.textContent = "No loved names yet.";
      list.appendChild(empty);
      return;
    }

    history.forEach((item) => {
      const li = document.createElement("li");
      const strong = document.createElement("strong");
      const span = document.createElement("span");
      strong.textContent = item.name;
      span.textContent = item.context || "Loved name";
      li.append(strong, span);
      list.appendChild(li);
    });
  }

  window.NamEnginePetTasteHistory = {
    add(name, context) {
      if (!name) return;
      const history = readHistory().filter((item) => item.name !== name);
      history.unshift({
        name,
        context: context || "Loved name",
        savedAt: new Date().toISOString(),
      });
      writeHistory(history);
      render();
    },
    render,
  };

  render();
})();
