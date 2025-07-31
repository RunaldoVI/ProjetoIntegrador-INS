function loadProfile() {
  const user = JSON.parse(localStorage.getItem("user"));
  if (!user || !user.email) {
    window.location.href = "sections/login.html";
    return;
  }

  fetch(`http://localhost:5000/api/user/profile?email=${encodeURIComponent(user.email)}`)
    .then((res) => {
      if (!res.ok) throw new Error("Erro ao carregar perfil");
      return res.json();
    })
    .then((dados) => {
      document.getElementById("user-name").textContent = dados.nome || "—";
      document.getElementById("user-info").textContent = `Utilizador registado com o email ${dados.email || "—"}`;
      document.getElementById("profile-nome").textContent = dados.nome || "—";
      document.getElementById("profile-email").textContent = dados.email || "—";
      document.getElementById("profile-funcao").textContent = dados.funcao || "—";
      document.getElementById("profile-inst").textContent = dados.instituicao || "—";

      const avatarImg = document.getElementById("user-avatar");
      avatarImg.src = `assets/avatars/${dados.avatar || "default.png"}`;
      avatarImg.onerror = () => (avatarImg.src = "assets/avatar.png");

      const historico = document.getElementById("pdf-history");
      historico.innerHTML = "";
      if (dados.pdfs && dados.pdfs.length > 0) {
        dados.pdfs.forEach((pdf) => {
          const li = document.createElement("li");
          li.textContent = `${pdf.nome} (${pdf.data})`;
          historico.appendChild(li);
        });
      } else {
        historico.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
      }

      localStorage.setItem("user", JSON.stringify(dados));
    })
    .catch((err) => {
      console.error("Erro ao carregar perfil:", err);
    });
}