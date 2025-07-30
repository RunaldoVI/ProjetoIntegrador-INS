function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-link");
  const sections = document.querySelectorAll(".section");
  const externalContentContainer = document.getElementById("external-content");

  navButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const target = btn.getAttribute("data-section");

      // Atualiza estilo ativo
      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Esconde todas as seções visíveis
      sections.forEach((section) => section.classList.add("hidden"));
      if (externalContentContainer) externalContentContainer.classList.add("hidden");

      if (target === "profile") {
        if (externalContentContainer && !externalContentContainer.dataset.loaded) {
          try {
            const response = await fetch("profile.html");
            const html = await response.text();
            externalContentContainer.innerHTML = html;
            externalContentContainer.dataset.loaded = "true";
          } catch (error) {
            externalContentContainer.innerHTML = "<p class='text-red-500'>Erro ao carregar perfil.</p>";
          }
        }

        if (externalContentContainer) {
          externalContentContainer.classList.remove("hidden");
        }
      } else {
        const visibleSection = document.getElementById(`section-${target}`);
        if (visibleSection) visibleSection.classList.remove("hidden");
      }
    });
  });
}
