const routes = {
  "#ingest": { html: "sections/ingest.html", js: "js/ingest.js" },
  "#history": { html: "sections/history.html", js: "js/history.js" },
  "#profile": { html: "sections/profile.html", js: "js/profile.js" },
  "#about": { html: "sections/about.html", js: "js/about.js" },
};

function updateActiveNav(route) {
  document.querySelectorAll(".nav-link").forEach(link => {
    link.classList.remove("text-accent", "font-bold");
    if (link.getAttribute("href") === route) {
      link.classList.add("text-accent", "font-bold");
    }
  });
}

async function handleRouteChange() {
  const hash = window.location.hash || "#ingest";
  const route = routes[hash] ?? routes["#ingest"];
  updateActiveNav(hash);
  const container = document.getElementById("external-content");
  if (!container) return;

  try {
    const htmlRes = await fetch(route.html);
    if (!htmlRes.ok) throw new Error("Erro ao carregar HTML.");
    const html = await htmlRes.text();
    container.innerHTML = html;

    const script = document.createElement("script");
    script.src = route.js;
    script.defer = true;

    // Chama a função certa: loadIngest, loadProfile, etc.
    script.onload = () => {
      const funcName = `load${hash.slice(1).charAt(0).toUpperCase()}${hash.slice(2)}`;
      if (typeof window[funcName] === "function") {
        window[funcName]();
      }
    };

    document.body.appendChild(script);
  } catch (err) {
    container.innerHTML = `<div class="text-red-600 p-4">Erro ao carregar a seção: ${hash}</div>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.addEventListener("hashchange", handleRouteChange);
  handleRouteChange();
});
