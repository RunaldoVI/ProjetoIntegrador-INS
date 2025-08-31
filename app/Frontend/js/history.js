console.log("✅ history.js carregado!");

// Helper igual ao profile.js
function readUserAnyStorage() {
  const ls = localStorage.getItem("user");
  const ss = sessionStorage.getItem("user");
  try {
    return ls ? JSON.parse(ls) : (ss ? JSON.parse(ss) : null);
  } catch {
    return null;
  }
}

// Usa getUser() do auth.js se existir; senão fallback
const currentUser = (typeof getUser === "function") ? getUser() : readUserAnyStorage();
console.log("📌 [history.js] user lido:", currentUser);

if (!currentUser || !currentUser.email) {
  console.warn("⚠️ [history.js] utilizador não autenticado, redirecionar...");
  window.location.href = "../sections/login.html";
  throw new Error("Histórico bloqueado: utilizador não autenticado");
}

// ---- Render do histórico global ----
(() => {
  const lista = document.getElementById("pdf-history");
  if (!lista) return;

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
