// Validação básica de email
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Mostrar alerta (pode ser substituído por toast customizado)
function showAlert(msg) {
  alert(msg);
}

// Função de registo
async function register() {
  const nome = document.getElementById("nome").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  // Campos obrigatórios
  if (!nome || !email || !password) {
    showAlert("Por favor, preencha todos os campos.");
    return;
  }

  if (!isValidEmail(email)) {
    showAlert("Por favor, insira um email válido.");
    return;
  }

  try {
    const res = await fetch("http://localhost:5000/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome,
        email,
        password,
        funcao: "Estudante",
        instituicao: "INS - Instituto de Ensino",
        avatar: "default.png" // <- obrigatório para corresponder à tua tabela
      })
    });

    if (res.status === 409) throw new Error("Este email já está registado.");
    if (!res.ok) throw new Error("Erro ao registar utilizador.");

    const data = await res.json();

    localStorage.setItem("user", JSON.stringify({
      nome,
      email,
      funcao: "Estudante",
      instituicao: "INS - Instituto de Ensino",
      avatar: "default.png"
    }));

    showAlert("Conta criada com sucesso!");
    window.location.href = "../index.html#ingest";
  } catch (err) {
    console.error("Erro no registo:", err);
    showAlert(err.message || "Erro inesperado no registo.");
  }
}

// Função de login
async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !password) {
    showAlert("Preencha todos os campos.");
    return;
  }

  try {
    const res = await fetch("http://localhost:5000/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) throw new Error("Email ou palavra-passe incorreta.");

    const data = await res.json();

    localStorage.setItem("user", JSON.stringify({
      nome: data.nome,
      email: data.email,
      funcao: data.funcao,
      instituicao: data.instituicao
    }));

    window.location.href = "../index.html#ingest";
  } catch (err) {
    console.error("Erro no login:", err);
    showAlert(err.message || "Erro ao autenticar.");
  }
}

// Logout
function logout() {
  localStorage.removeItem("user");
  window.location.href = "../sections/login.html";
}

// Verificação de sessão ao carregar
document.addEventListener("DOMContentLoaded", () => {
  const user = JSON.parse(localStorage.getItem("user"));
  const input = document.getElementById("pdfInput");
  const authButtons = document.getElementById("authButtons");
  const logoutBtn = document.getElementById("logoutBtn");

  const isLoggedIn = user && user.email;

  if (authButtons) authButtons.classList.toggle("hidden", isLoggedIn);
  if (logoutBtn) logoutBtn.classList.toggle("hidden", !isLoggedIn);
  if (input) input.classList.remove("hidden");
});
