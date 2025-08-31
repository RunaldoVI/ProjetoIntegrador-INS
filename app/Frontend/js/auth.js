/* =========================================================
   Utils
========================================================= */

// Helper para listeners que só liga se o elemento existir
function on(el, evt, fn) {
  if (el) el.addEventListener(evt, fn);
}

// ÚNICA getUser (global) + logs simples
window.getUser = function getUser() {
  const localStr = localStorage.getItem("user");
  const sessionStr = sessionStorage.getItem("user");

  console.log("[auth.getUser] localStorage:", localStr);
  console.log("[auth.getUser] sessionStorage:", sessionStr);

  const raw = localStr !== null ? localStr : sessionStr;
  const user = raw ? JSON.parse(raw) : null;

  console.log("[auth.getUser] return:", user);
  return user;
};

// Validação básica de email
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Popup de feedback
function showAlert(message, type = "error") {
  const popup = document.getElementById("popup");
  const popupMessage = document.getElementById("popup-message");
  if (!popup || !popupMessage) return;

  popupMessage.textContent = message;

  if (type === "success") {
    popup.classList.remove("bg-red-600");
    popup.classList.add("bg-green-600");
  } else {
    popup.classList.remove("bg-green-600");
    popup.classList.add("bg-red-600");
  }

  popup.classList.remove("hidden");
  setTimeout(() => {
    popup.classList.remove("translate-y-10", "opacity-0");
    popup.classList.add("translate-y-0", "opacity-100");
  }, 10);

  setTimeout(() => {
    popup.classList.remove("translate-y-0", "opacity-100");
    popup.classList.add("translate-y-10", "opacity-0");
    setTimeout(() => popup.classList.add("hidden"), 500);
  }, 3000);
}

// debounce para pesquisas
function debounce(fn, wait = 250) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

// Fallback de bandeira por código CCA2
function flagEmojiFromCCA2(code = "") {
  return code
    .toUpperCase()
    .replace(/./g, ch => String.fromCodePoint(127397 + ch.charCodeAt()));
}

/* =========================================================
   Auth: Registo, Login, Logout
========================================================= */

async function register() {
  const nome = (document.getElementById("nome") || {}).value?.trim() || "";
  const email = (document.getElementById("email") || {}).value?.trim() || "";
  const password = (document.getElementById("password") || {}).value?.trim() || "";
  const funcao = (document.getElementById("funcao") || {}).value?.trim() || "";
  const instituicao = (document.getElementById("instituicao") || {}).value?.trim() || "";
  const avatarInput = document.getElementById("avatar");
  const avatarFile = avatarInput && avatarInput.files ? avatarInput.files[0] : null;

  if (!nome || !email || !password || !funcao || !instituicao) {
    showAlert("Preencha todos os campos.");
    return;
  }
  if (!isValidEmail(email)) {
    showAlert("Email inválido.");
    return;
  }
  if (avatarFile && !avatarFile.name.toLowerCase().endsWith(".png")) {
    showAlert("Por favor, selecione uma imagem em formato .png");
    return;
  }

  const formData = new FormData();
  formData.append("nome", nome);
  formData.append("email", email);
  formData.append("password", password);
  formData.append("funcao", funcao);
  formData.append("instituicao", instituicao);
  if (avatarFile) formData.append("avatar", avatarFile);

  try {
    const res = await fetch("http://localhost:5000/api/register", {
      method: "POST",
      body: formData
    });

    if (res.status === 409) throw new Error("Email já registado.");
    if (!res.ok) throw new Error("Erro ao registar.");

    showAlert("Conta criada com sucesso!", "success");
    setTimeout(() => { window.location.href = "../sections/login.html"; }, 1500);
  } catch (err) {
    console.error("Erro no registo:", err);
    showAlert(err.message || "Erro ao registar.");
  }
}

async function login() {
  const email = (document.getElementById("email") || {}).value?.trim() || "";
  const password = (document.getElementById("password") || {}).value || "";
  const rememberMeEl = document.getElementById("rememberMe");
  const lembrar = rememberMeEl ? !!rememberMeEl.checked : false;

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

    const serialized = JSON.stringify(userData);
    if (lembrar) {
      localStorage.setItem("user", serialized);
      sessionStorage.removeItem("user");
      console.log("[auth.login] guardado em localStorage");
    } else {
      sessionStorage.setItem("user", serialized);
      localStorage.removeItem("user");
      console.log("[auth.login] guardado em sessionStorage");
    }

    showAlert("Login realizado com sucesso!", "success");
    setTimeout(() => { window.location.href = "../index.html#ingest"; }, 2000);
  } catch (err) {
    console.error("Erro no login:", err);
    showAlert(err.message || "Erro ao autenticar.");
  }
}

function logout() {
  localStorage.removeItem("user");
  sessionStorage.removeItem("user");
  const toLogin = location.pathname.includes("/sections/") ? "./login.html" : "../sections/login.html";
  window.location.href = toLogin;
}

/* =========================================================
   Bootstrap + Modal País → Universidades
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  // Só a HOME/INGEST tem estes elementos
  const input = document.getElementById("pdfInput");
  const authButtons = document.getElementById("authButtons");
  const logoutBtn = document.getElementById("logoutBtn");

  const pageUsesHeader = !!(input || authButtons || logoutBtn);

  // Se NÃO é a home (perfil, histórico, etc.), não validar nem redirecionar aqui.
  if (!pageUsesHeader) {
    console.log("[auth] página interna; não vou validar nem redirecionar aqui.");
    return;
  }

  // ---- Gestão da home/ingest ----
  const user = getUser();

  if (user && user.email) {
    fetch("http://localhost:5000/api/user/profile?email=" + encodeURIComponent(user.email))
      .then(res => {
        console.log("[auth] validação perfil status:", res.status);
        if (!res.ok) throw new Error("Sessão inválida");
        return res.json();
      })
      .then(() => {
        authButtons?.classList.add("hidden");
        logoutBtn?.classList.remove("hidden");
        input?.classList.remove("hidden");
      })
      .catch(err => {
        console.warn("[auth] validação falhou:", err);
        localStorage.removeItem("user");
        sessionStorage.removeItem("user");
        //window.location.href = "../sections/login.html";
      });
  } else {
    authButtons?.classList.remove("hidden");
    logoutBtn?.classList.add("hidden");
    input?.classList.add("hidden");
  }


  // Avatar input (se existir)
  const avatarInput = document.getElementById("avatar");
  const avatarLabel = document.getElementById("avatarLabel");
  on(avatarInput, "change", () => {
    const file = avatarInput.files && avatarInput.files[0];
    if (avatarLabel) {
      avatarLabel.textContent = file ? "Arquivo: " + file.name : "Escolher Ficheiro";
    }
  });

  // --- Modal País → Universidades ---
  const instInput   = document.getElementById("instituicao");
  const instModal   = document.getElementById("instModal");
  const modalClose  = document.getElementById("modalClose");
  const modalCancel = document.getElementById("modalCancel");
  const modalBack   = document.getElementById("modalBack");
  const modalTitle  = document.getElementById("modalTitle");
  const modalList   = document.getElementById("modalList");
  const modalSearch = document.getElementById("modalSearch");

  // Se a página não tem modal, terminar aqui
  if (!(instInput && instModal && modalTitle && modalList && modalSearch)) {
    return;
  }

  const HIPOLABS_DATASET_URL =
    "https://raw.githubusercontent.com/Hipo/university-domains-list/master/world_universities_and_domains.json";

  let countries = [];        // [{displayName, apiName, flag, code}]
  let allUnis = [];          // dataset completo (fallback local)
  let universities = [];     // resultados correntes
  let currentCountry = null; // objeto do país selecionado
  let view = "countries";    // "countries" | "universities"

  on(instInput, "click", async () => {
    instModal.classList.remove("hidden");
    if (countries.length === 0) {
      modalList.innerHTML = "<p style='padding:1rem'>A carregar países...</p>";
      await loadCountries();
    }
    openCountriesView();
  });

  [modalClose, modalCancel].filter(Boolean).forEach(btn => {
    on(btn, "click", () => {
      instModal.classList.add("hidden");
      openCountriesView();
    });
  });

  document.addEventListener("keydown", e => {
    if (!instModal.classList.contains("hidden") && e.key === "Escape") {
      instModal.classList.add("hidden");
      openCountriesView();
    }
  });

  on(instModal, "click", e => {
    if (e.target === instModal) {
      instModal.classList.add("hidden");
      openCountriesView();
    }
  });

  on(modalBack, "click", openCountriesView);

  function openCountriesView() {
    view = "countries";
    currentCountry = null;
    universities = [];
    modalTitle.textContent = "Escolha um país";
    if (modalBack) modalBack.disabled = true;
    modalSearch.value = "";
    renderCountries(countries);
    setTimeout(() => modalSearch.focus(), 10);
  }

  async function loadCountries() {
    try {
      const res = await fetch(HIPOLABS_DATASET_URL, { cache: "no-store" });
      const data = await res.json();
      allUnis = Array.isArray(data) ? data : [];

      const set = new Set(allUnis.map(u => u.country).filter(Boolean));
      const names = Array.from(set).sort((a, b) =>
        a.localeCompare(b, "en", { sensitivity: "base" })
      );

      countries = names.map(n => ({
        displayName: n,
        apiName: n,
        flag: null,
        code: ""
      }));

      try {
        const rc = await fetch("https://restcountries.com/v3.1/all?fields=name,cca2,flags")
          .then(r => r.json());
        const byName = new Map(
          rc.map(c => [c && c.name && c.name.common, { flag: (c.flags && (c.flags.png || c.flags.svg)) || null, code: c.cca2 || "" }])
        );
        countries = countries.map(c => {
          const m = byName.get(c.apiName);
          return m ? { ...c, flag: m.flag, code: m.code } : c;
        });
      } catch (_) {
        // sem flags se falhar
      }

    } catch (e) {
      console.error(e);
      modalList.innerHTML = "<p style='padding:1rem;color:#b91c1c'>Erro ao carregar países.</p>";
    }
  }

  function renderCountries(list) {
    modalList.innerHTML = "";
    if (!list || list.length === 0) {
      modalList.innerHTML = "<p style='padding:1rem'>Nenhum país encontrado.</p>";
      return;
    }

    const frag = document.createDocumentFragment();
    list.forEach(c => {
      const item = document.createElement("div");
      item.className = "modal__item";
      item.setAttribute("role", "button");
      item.setAttribute("tabindex", "0");

      if (c.flag) {
        const img = document.createElement("img");
        img.className = "flag";
        img.loading = "lazy";
        img.src = c.flag;
        img.alt = c.displayName;
        img.onerror = () => {
          const span = document.createElement("span");
          span.textContent = flagEmojiFromCCA2(c.code || "");
          span.style = "font-size:18px;width:24px;display:inline-block;text-align:center;";
          img.replaceWith(span);
        };
        item.appendChild(img);
      } else {
        const span = document.createElement("span");
        span.textContent = flagEmojiFromCCA2(c.code || "");
        span.style = "font-size:18px;width:24px;display:inline-block;text-align:center;";
        item.appendChild(span);
      }

      const label = document.createElement("span");
      label.textContent = " " + c.displayName;
      item.appendChild(label);

      const choose = () => selectCountry(c);
      on(item, "click", choose);
      on(item, "keydown", e => {
        if (e.key === "Enter" || e.key === " ") choose();
      });

      frag.appendChild(item);
    });
    modalList.appendChild(frag);
  }

  async function selectCountry(countryObj) {
    view = "universities";
    currentCountry = countryObj;
    modalTitle.textContent = "Universidades em " + countryObj.displayName;
    if (modalBack) modalBack.disabled = false;
    modalSearch.value = "";
    universities = [];

    modalList.innerHTML =
      "<p style='padding:1rem;color:#374151'>Escreva pelo menos 2 letras para pesquisar universidades em " +
      countryObj.displayName + ".</p>";

    setTimeout(() => modalSearch.focus(), 20);
  }

  async function fetchUniversitiesFiltered(countryEn, term) {
    const qs = new URLSearchParams({ country: countryEn, name: term || "" });
    const url = "https://universities.hipolabs.com/search?" + qs.toString();
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("Falha ao obter universidades");
    return await res.json();
  }

  function localFilterUniversities(countryEn, term) {
    const t = (term || "").toLowerCase();
    return allUnis.filter(
      u =>
        u.country === countryEn &&
        (!t || ((u.name || "").toLowerCase().includes(t)))
    );
  }

  function renderUniversities(list) {
    modalList.innerHTML = "";
    if (!list || list.length === 0) {
      modalList.innerHTML = "<p style='padding:1rem'>Nenhuma universidade encontrada.</p>";
      return;
    }

    const take = 300;
    const slice = list.slice(0, take);
    const frag = document.createDocumentFragment();

    slice.forEach(u => {
      const item = document.createElement("div");
      item.className = "modal__item";
      item.setAttribute("role", "button");
      item.setAttribute("tabindex", "0");
      item.textContent = u.name || "-";
      item.title = (u.web_pages && u.web_pages[0]) || "";

      const choose = () => {
        const instEl = document.getElementById("instituicao");
        if (instEl) instEl.value = u.name || "";
        instModal.classList.add("hidden");
        openCountriesView();
      };

      on(item, "click", choose);
      on(item, "keydown", e => {
        if (e.key === "Enter" || e.key === " ") choose();
      });

      frag.appendChild(item);
    });

    modalList.appendChild(frag);

    if (list.length > take) {
      const more = document.createElement("button");
      more.className = "btn-secondary";
      more.style.margin = "0.75rem";
      more.textContent = "Carregar mais (" + (list.length - take) + ")";
      on(more, "click", () => renderUniversities(list.slice(take)));
      modalList.appendChild(more);
    }
  }

  const handleSearch = debounce(async () => {
    const term = (modalSearch.value || "").trim();

    if (view === "countries") {
      const t = term.toLowerCase();
      const filtered = countries.filter(c => c.displayName.toLowerCase().includes(t));
      renderCountries(filtered);
      return;
    }

    if (!currentCountry) return;
    if (term.length < 2) {
      modalList.innerHTML =
        "<p style='padding:1rem;color:#374151'>Escreva pelo menos 2 letras para pesquisar universidades.</p>";
      return;
    }

    const countryApi = currentCountry.apiName;
    modalList.innerHTML = "<p style='padding:1rem'>A procurar...</p>";
    try {
      const list = await fetchUniversitiesFiltered(countryApi, term);
      if (Array.isArray(list) && list.length) {
        universities = list;
        renderUniversities(universities);
      } else {
        universities = localFilterUniversities(countryApi, term);
        renderUniversities(universities);
      }
    } catch (e) {
      console.error(e);
      universities = localFilterUniversities(countryApi, term);
      renderUniversities(universities);
    }
  }, 300);

  on(modalSearch, "input", handleSearch);

  // Select custom de função (se existir na página)
  const funcaoSelect = document.getElementById("funcaoSelect");
  if (!funcaoSelect) return;

  const trigger = funcaoSelect.querySelector(".select-trigger");
  const menu    = funcaoSelect.querySelector(".select-menu");
  const hidden  = funcaoSelect.querySelector("input[type=hidden]");
  const text    = funcaoSelect.querySelector(".select-text");

  on(trigger, "click", () => {
    if (!menu) return;
    menu.classList.toggle("hidden");
    funcaoSelect.classList.toggle("open");
  });

  document.addEventListener("click", e => {
    if (!funcaoSelect.contains(e.target)) {
      if (menu) menu.classList.add("hidden");
      funcaoSelect.classList.remove("open");
    }
  });

  if (menu) {
    menu.querySelectorAll(".option").forEach(opt => {
      on(opt, "click", () => {
        const val = opt.getAttribute("data-value");
        if (hidden) hidden.value = val;
        if (text) text.textContent = val;
        funcaoSelect.classList.add("has-value");
        menu.classList.add("hidden");
        funcaoSelect.classList.remove("open");
      });
    });
  }
});
