
document.addEventListener("DOMContentLoaded", () => {
  const user = JSON.parse(localStorage.getItem("user"));

  if (!user || !user.email) {
    window.location.href = "login.html";
    return;
  }

  // Preenche dados locais
  document.getElementById("user-name").textContent = user.nome;
  document.getElementById("user-info").textContent = `Utilizador registado com o email ${user.email}`;
  document.getElementById("profile-nome").textContent = user.nome;
  document.getElementById("profile-email").textContent = user.email;
  document.getElementById("user-avatar").src = "assets/avatar.png";

  // Histórico inicial vazio
  const historico = document.getElementById("pdf-history");
  historico.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";

  // Carrega dados reais do backend com email
  fetch(`http://localhost:5000/api/user/profile?email=${encodeURIComponent(user.email)}`)
    .then((res) => {
      if (!res.ok) throw new Error("Erro ao carregar perfil.");
      return res.json();
    })
    .then((dados) => {
      document.getElementById("profile-funcao").textContent = dados.funcao || "Estudante";
      document.getElementById("profile-inst").textContent = dados.instituicao || "Instituição";

      const ul = document.getElementById("pdf-history");
      ul.innerHTML = "";

      if (dados.pdfs && dados.pdfs.length > 0) {
        dados.pdfs.forEach((pdf) => {
          const li = document.createElement("li");
          li.innerHTML = `${pdf.nome} <span class="text-xs text-gray-400">(${pdf.data})</span>`;
          ul.appendChild(li);
        });
      } else {
        ul.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
      }
    })
    .catch((err) => {
      console.warn("Erro ao carregar perfil:", err);
    });
});

// Abre o modal de edição com os dados atuais
function openEditModal() {
  document.getElementById("editModal").classList.remove("hidden");
  document.getElementById("editNome").value = document.getElementById("profile-nome").textContent;
  document.getElementById("editFuncao").value = document.getElementById("profile-funcao").textContent;
  document.getElementById("editInstituicao").value = document.getElementById("profile-inst").textContent;
}

// Fecha o modal de edição
function closeEditModal() {
  document.getElementById("editModal").classList.add("hidden");
}

// Submete o novo perfil para o backend
function submitProfileEdit() {
  const nome = document.getElementById("editNome").value.trim();
  const funcao = document.getElementById("editFuncao").value.trim();
  const instituicao = document.getElementById("editInstituicao").value.trim();
  const email = JSON.parse(localStorage.getItem("user")).email;

fetch("http://localhost:5000/api/user/profile", {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, nome, funcao, instituicao })
})

    .then((res) => {
      if (!res.ok) throw new Error("Erro ao atualizar perfil.");
      return res.json();
    })
    .then(() => {
      localStorage.setItem("user", JSON.stringify({ nome, email }));
      location.reload();
    })
    .catch((err) => {
      alert(err.message || "Erro ao atualizar.");
    });
}
