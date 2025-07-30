// Função de registo
function register() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !password) {
    alert("Preencha todos os campos.");
    return;
  }

  const users = JSON.parse(localStorage.getItem("users") || "{}");

  if (users[email]) {
    alert("Este email já está registado.");
    return;
  }

  users[email] = { password };
  localStorage.setItem("users", JSON.stringify(users));
  alert("Registo feito com sucesso!");
  window.location.href = "login.html";
}

// Função de login
function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  const users = JSON.parse(localStorage.getItem("users") || "{}");

  if (users[email] && users[email].password === password) {
    localStorage.setItem("loggedInUser", email);
    window.location.href = "index.html";
  } else {
    alert("Email ou palavra-passe inválidos.");
  }
}

// Verifica se está autenticado
function checkAuth() {
  const loggedIn = localStorage.getItem("loggedInUser");
  if (!loggedIn) {
    window.location.href = "login.html";
  }
}

// Logout
function logout() {
  localStorage.removeItem("loggedInUser");
  window.location.href = "login.html";
}

// Lógica ao carregar a página
document.addEventListener("DOMContentLoaded", () => {
  const loggedIn = localStorage.getItem("loggedInUser");
  const input = document.getElementById("pdfInput");
  const authButtons = document.getElementById("authButtons");
  const logoutBtn = document.getElementById("logoutBtn");

  if (loggedIn) {
    if (authButtons) authButtons.classList.add("hidden");
    if (logoutBtn) logoutBtn.classList.remove("hidden");
  } else {
    if (authButtons) authButtons.classList.remove("hidden");
    if (logoutBtn) logoutBtn.classList.add("hidden");
  }

  // Mostrar sempre o input do PDF
  if (input) input.classList.remove("hidden");
});
