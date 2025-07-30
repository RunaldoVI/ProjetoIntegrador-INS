// js/main.js
document.addEventListener("DOMContentLoaded", () => {
  window.addEventListener("hashchange", handleRouteChange);
  handleRouteChange(); // Executa na primeira vez
});

const routes = {
  "#ingest": {
    html: "sections/ingest.html",
    js: "js/ingest.js"
  },
  "#history": {
    html: "sections/history.html",
    js: "js/history.js"
  },
  "#profile": {
    html: "sections/profile.html",
    js: "js/profile.js"
  },
  "#about": {
    html: "sections/about.html",
    js: "js/about.js"
  }
};

async function handleRouteChange() {
  const hash = window.location.hash || "#ingest";
  const route = routes[hash] ?? routes["#ingest"];

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
    document.body.appendChild(script);
  } catch (err) {
    container.innerHTML = `<div class="bg-red-100 text-red-800 p-4 rounded shadow">Erro ao carregar a seção: ${hash.replace("#", "")}</div>`;
    console.error("Erro ao carregar seção:", err);
  }
}
