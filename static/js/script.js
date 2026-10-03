document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-confirm]").forEach(btn => {
    btn.addEventListener("click", e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });
});
