console.log("✅ history.js carregado!");

// Ler utilizador de forma unificada (localStorage ou sessionStorage)
const user = (typeof getUser === "function" ? getUser() : (() => {
  const raw = localStorage.getItem("user") || sessionStorage.getItem("user");
  console.log("✅ [history.js] carregado!");
  
  console.log("📌 [history.js] user lido:", user);
  return raw ? JSON.parse(raw) : null;
})());


if (!user || !user.email) {
  console.warn("⚠️ [history.js] utilizador não autenticado, redirecionar...");
  window.location.href = "../sections/login.html";
  throw new Error("Histórico bloqueado: utilizador não autenticado");
}

(() => {
  const lista = document.getElementById("pdf-history");

  fetch("http://localhost:5000/api/pdf/todos")
    .then(res => res.json())
    .then(data => {
      if (data.historico && data.historico.length > 0) {
        const items = data.historico.map(item => `
          <li class="flex items-center justify-between">
            <div>
              <strong>${item.nome_utilizador}</strong> ingeriu 📄 <em>${item.nome_pdf}</em>
            </div>
            <span class="text-xs text-gray-500">${item.data}</span>
          </li>
        `).join("");
        lista.innerHTML = items;
      } else {
        lista.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
      }
    })
    .catch(err => {
      console.error("Erro ao carregar histórico global:", err);
      lista.innerHTML = "<li>Erro ao carregar histórico.</li>";
    });
})();
