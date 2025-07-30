function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-link");
  const sections = document.querySelectorAll(".section");

  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-section");

      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      sections.forEach((section) => section.classList.add("hidden"));
      const visibleSection = document.getElementById(`section-${target}`);
      if (visibleSection) visibleSection.classList.remove("hidden");
    });
  });
}
