// router.js
function loadPage(route) {
  const content = document.getElementById("external-content");
  if (!content) return;

  content.innerHTML = "A carregar...";

  fetch(`sections/${route}.html`)
    .then(res => {
      if (!res.ok) throw new Error("Página não encontrada.");
      return res.text();
    })
    .then(html => {
      content.innerHTML = html;

      const script = document.createElement("script");
      script.src = `js/${route}.js`;
      script.defer = true;
      document.body.appendChild(script);
    })
    .catch(err => {
      content.innerHTML = `<p class="text-red-500">Erro ao carregar ${route}.html</p>`;
      console.error(err);
    });
}

function handleRouting() {
  const route = location.hash.replace("#", "") || "ingest";
  loadPage(route);
}

window.addEventListener("hashchange", handleRouting);
window.addEventListener("DOMContentLoaded", () => {
  handleRouting();

  document.querySelectorAll(".nav-link").forEach(btn => {
    btn.addEventListener("click", () => {
      const route = btn.dataset.section;
      location.hash = route; // Isto dispara o hashchange
      document.querySelectorAll(".nav-link").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });
});
