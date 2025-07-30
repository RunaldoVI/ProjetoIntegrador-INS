// Função de registo
function register() {
  const nome = document.getElementById("nome").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!nome || !email || !password) {
    alert("Por favor, preencha todos os campos.");
    return;
  }

  fetch("http://localhost:5000/api/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nome,
      email,
      password,
      funcao: "Estudante",
      instituicao: "INS - Instituto de Ensino"
    })
  })
    .then((res) => {
      if (res.status === 409) throw new Error("Email já registado.");
      if (!res.ok) throw new Error("Erro ao registar utilizador.");
      return res.json();
    })
    .then(() => {
      localStorage.setItem("user", JSON.stringify({ nome, email }));
      alert("Conta criada com sucesso!");
      window.location.href = "index.html";
    })
    .catch((err) => {
      console.error("Erro no registo:", err);
      alert(err.message || "Erro inesperado.");
    });
}

// Função de login
function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !password) {
    alert("Preencha todos os campos.");
    return;
  }

  fetch("http://localhost:5000/api/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  })
    .then((res) => {
      if (!res.ok) throw new Error("Email ou palavra-passe incorreta.");
      return res.json();
    })
    .then((data) => {
      localStorage.setItem("user", JSON.stringify({ 
        nome: data.nome, 
        email: data.email,
        funcao: data.funcao,
        instituicao: data.instituicao
      }));
      window.location.href = "index.html";
    })
    .catch((err) => {
      console.error("Erro no login:", err);
      alert(err.message || "Erro ao autenticar.");
    });
}

// Logout
function logout() {
  localStorage.removeItem("user");
  window.location.href = "login.html";
}

// Verificação de sessão ao carregar
document.addEventListener("DOMContentLoaded", () => {
  const user = JSON.parse(localStorage.getItem("user"));
  const input = document.getElementById("pdfInput");
  const authButtons = document.getElementById("authButtons");
  const logoutBtn = document.getElementById("logoutBtn");

  if (user && user.email) {
    if (authButtons) authButtons.classList.add("hidden");
    if (logoutBtn) logoutBtn.classList.remove("hidden");
  } else {
    if (authButtons) authButtons.classList.remove("hidden");
    if (logoutBtn) logoutBtn.classList.add("hidden");
  }

  if (input) input.classList.remove("hidden");
});
