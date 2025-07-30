// Pega o ID da URL: profile.html?id=3
const params = new URLSearchParams(window.location.search);
const userId = params.get("id");

if (!userId) {
  document.getElementById("profile-container").innerText = "ID de usuário não informado.";
} else {
  fetch(`/api/users/${userId}/profile`)
    .then((res) => {
      if (!res.ok) throw new Error("Usuário não encontrado.");
      return res.json();
    })
    .then((data) => {
      const container = document.getElementById("profile-container");
      container.innerHTML = `
        <div class="profile-card">
          <img src="${data.avatarUrl || '/assets/default.png'}" alt="Avatar" width="150" />
          <h2>${data.name}</h2>
          <p>${data.bio || "Sem descrição."}</p>
          <h3>Competências</h3>
          <ul>
            ${(data.skills || []).map((s) => `<li>${s}</li>`).join("")}
          </ul>
        </div>
      `;
    })
    .catch((err) => {
      document.getElementById("profile-container").innerText = "Erro ao carregar perfil.";
      console.error(err);
    });
}
document.addEventListener("DOMContentLoaded", () => {
  const user = JSON.parse(localStorage.getItem("user"));
  if (!user || !user.id) {
    window.location.href = "login.html";
    return;
  }

  fetch(`/api/users/${user.id}/profile`)
    .then((res) => res.json())
    .then((data) => {
      document.getElementById("nome").textContent = data.name;
      document.getElementById("email").textContent = data.email;
      document.getElementById("bio").textContent = data.bio || "Estudante";
      document.getElementById("instituicao").textContent = data.instituicao || "Instituição não definida";

      const historico = document.getElementById("pdf-historico");
      if (data.pdfs && data.pdfs.length > 0) {
        historico.innerHTML = data.pdfs
          .map((pdf) => `<li>${pdf.nome} (${pdf.data})</li>`)
          .join("");
      } else {
        historico.innerHTML = "<li>Nenhum PDF ingerido</li>";
      }
    });
});

