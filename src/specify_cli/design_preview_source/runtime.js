(() => {
  const body = document.body;
  const tabs = Array.from(
    document.querySelectorAll(".direction-tabs [data-direction-target]"),
  );
  const directionIds = tabs
    .map((tab) => tab.getAttribute("data-direction-target") || "")
    .filter(Boolean);

  function activate(directionId) {
    if (!directionIds.includes(directionId)) {
      directionId = directionIds[0] || "direction-a";
    }
    body.dataset.activeDirection = directionId;
    tabs.forEach((tab) => {
      const active = tab.getAttribute("data-direction-target") === directionId;
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  function directionFromHash() {
    const raw = (location.hash || "").replace(/^#/, "").trim();
    return raw || directionIds[0] || "direction-a";
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      const directionId = tab.getAttribute("data-direction-target") || "";
      if (!directionId) return;
      event.preventDefault();
      if (location.hash !== `#${directionId}`) {
        location.hash = directionId;
      } else {
        activate(directionId);
      }
    });
  });

  window.addEventListener("hashchange", () => {
    activate(directionFromHash());
  });

  activate(directionFromHash());
})();
