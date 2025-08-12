// Validação básica de email
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Mostrar alerta
function showAlert(msg) {
  alert(msg);
}

// Obter utilizador autenticado de qualquer storage
function getUser() {
  const raw = localStorage.getItem("user") || sessionStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

// Função de registo
async function register() {
  const nome = document.getElementById("nome").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const funcao = document.getElementById("funcao").value.trim();
  const instituicao = document.getElementById("instituicao").value.trim();
  const avatarFile = document.getElementById("avatar").files[0];

  if (!nome || !email || !password || !funcao || !instituicao) {
    showAlert("Preenche todos os campos.");
    return;
  }


  if (avatarFile && !avatarFile.name.endsWith(".png")) {
  showAlert("Por favor seleciona uma imagem em formato .png");
  return;
}

  const formData = new FormData();
  formData.append("nome", nome);
  formData.append("email", email);
  formData.append("password", password);
  formData.append("funcao", funcao);
  formData.append("instituicao", instituicao);
  if (avatarFile) {
    formData.append("avatar", avatarFile);
  }

  try {
    const res = await fetch("http://localhost:5000/api/register", {
      method: "POST",
      body: formData
    });

    if (res.status === 409) throw new Error("Email já registado.");
    if (!res.ok) throw new Error("Erro ao registar.");

    showAlert("Conta criada com sucesso!");
    window.location.href = "../sections/login.html";
  } catch (err) {
    console.error("Erro no registo:", err);
    showAlert(err.message || "Erro ao registar.");
  }
}

// Função de login
async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const lembrar = document.getElementById("rememberMe")?.checked;

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
    const userData = {
      nome: data.nome,
      email: data.email,
      funcao: data.funcao,
      instituicao: data.instituicao,
      avatar: data.avatar || "default.png"
    };

    if (lembrar) {
      localStorage.setItem("user", JSON.stringify(userData));
    } else {
      sessionStorage.setItem("user", JSON.stringify(userData));
    }

    window.location.href = "../index.html#ingest";
  } catch (err) {
    console.error("Erro no login:", err);
    showAlert(err.message || "Erro ao autenticar.");
  }
}

// Logout
function logout() {
  localStorage.removeItem("user");
  sessionStorage.removeItem("user");
  window.location.href = "../sections/login.html";
}

// Verificação de sessão ao carregar
document.addEventListener("DOMContentLoaded", () => {
  const user = getUser();
  const input = document.getElementById("pdfInput");
  const authButtons = document.getElementById("authButtons");
  const logoutBtn = document.getElementById("logoutBtn");


    const avatarInput = document.getElementById("avatar");
  const avatarLabel = document.getElementById("avatarLabel");

  if (avatarInput && avatarLabel) {
    avatarInput.addEventListener("change", () => {
      const file = avatarInput.files[0];
      avatarLabel.textContent = file ? `📁 ${file.name}` : "📁 Escolher Ficheiro";
    });
  }

  if (user && user.email) {
    fetch(`http://localhost:5000/api/user/profile?email=${encodeURIComponent(user.email)}`)
      .then(res => {
        if (!res.ok) throw new Error("Sessão inválida");
        return res.json();
      })
      .then(data => {
        if (authButtons) authButtons.classList.add("hidden");
        if (logoutBtn) logoutBtn.classList.remove("hidden");
        if (input) input.classList.remove("hidden");
      })
      .catch(() => {
        localStorage.removeItem("user");
        sessionStorage.removeItem("user");
        window.location.href = "../sections/login.html";
      });
  } else {
    if (authButtons) authButtons.classList.remove("hidden");
    if (logoutBtn) logoutBtn.classList.add("hidden");
    if (input) input.classList.add("hidden");
  }
});
