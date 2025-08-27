// Validação básica de email
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Mostrar alerta (agora com pop-up customizado)
function showAlert(msg, type = "error") {
  const popup = document.getElementById("popup");
  const popupMessage = document.getElementById("popup-message");

  if (!popup || !popupMessage) {
    console.warn("Elemento de pop-up não encontrado no HTML.");
    return;
  }

  popupMessage.textContent = msg;

  // Cor dependendo do tipo
  if (type === "success") {
    popup.classList.remove("bg-red-600");
    popup.classList.add("bg-green-600");
  } else {
    popup.classList.remove("bg-green-600");
    popup.classList.add("bg-red-600");
  }

  popup.classList.remove("hidden", "opacity-0");
  popup.classList.add("opacity-100");

  // Esconde após 3 segundos
  setTimeout(() => {
    popup.classList.add("opacity-0");
    setTimeout(() => popup.classList.add("hidden"), 300);
  }, 3000);
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

    showAlert("Conta criada com sucesso!", "success");
    setTimeout(() => {
      window.location.href = "../sections/login.html";
    }, 1500);
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

    // ✅ Mostra toast e só depois redireciona
    showAlert("Login realizado com sucesso!", "success");

    // ✅ Bloqueia qualquer ação imediata de reload/redirecionamento
    setTimeout(() => {
      window.location.href = "../index.html#ingest";
    }, 2000); // 2s dá tempo para ver o toast

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
