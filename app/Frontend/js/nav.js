function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-link");
  const externalContentContainer = document.getElementById("external-content");

  navButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const target = btn.getAttribute("data-section");

      // Evita recarregamento desnecessário
      if (externalContentContainer.dataset.active === target) return;

      // Estilo ativo
      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Esconde e limpa
      externalContentContainer.classList.add("hidden");
      externalContentContainer.innerHTML = "";
      delete externalContentContainer.dataset.loaded;

      try {
        const htmlPath = `sections/${target}.html`;
        const jsPath = `js/${target}.js`;

        // Carrega HTML
        const response = await fetch(htmlPath);
        if (!response.ok) throw new Error("Erro ao carregar HTML.");
        const html = await response.text();
        externalContentContainer.innerHTML = html;
        externalContentContainer.classList.remove("hidden");
        externalContentContainer.dataset.loaded = "true";
        externalContentContainer.dataset.active = target;

        // Carrega script correspondente
        const script = document.createElement("script");
        script.src = jsPath;
        script.defer = true;
        document.body.appendChild(script);

      } catch (error) {
        externalContentContainer.innerHTML = `
          <div class="text-red-600 bg-red-100 p-4 rounded shadow">
            <strong>Erro ao carregar a seção:</strong> ${target}
          </div>`;
        externalContentContainer.classList.remove("hidden");
        console.error("Erro ao carregar seção:", error);
      }
    });
  });
}
