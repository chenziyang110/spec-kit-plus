(() => {
  const body = document.body;
  const canvases = Array.from(document.querySelectorAll("[data-direction-id]"));
  const directionIds = canvases
    .map((canvas) => canvas.getAttribute("data-direction-id") || "")
    .filter(Boolean);

  function activate(directionId) {
    if (!directionIds.includes(directionId)) {
      directionId = directionIds[0] || "direction-main";
    }
    body.dataset.activeDirection = directionId;
    canvases.forEach((canvas) => {
      const active = canvas.getAttribute("data-direction-id") === directionId;
      canvas.setAttribute("aria-hidden", active ? "false" : "true");
    });
  }

  function directionFromHash() {
    const raw = (location.hash || "").replace(/^#/, "").trim();
    return raw || directionIds[0] || "direction-main";
  }

  window.addEventListener("hashchange", () => {
    activate(directionFromHash());
  });

  activate(directionFromHash());
})();
