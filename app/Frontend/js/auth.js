/* =========================================================
   Utils
========================================================= */

// Validação básica de email
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showAlert(msg, type = "error") {
  const popup = document.getElementById("popup");
  const popupMessage = document.getElementById("popup-message");

  if (!popup || !popupMessage) return;

  popupMessage.textContent = msg;

  // Cor dependendo do tipo
  if (type === "success") {
    popup.classList.remove("bg-red-600");
    popup.classList.add("bg-green-600");
  } else {
    popup.classList.remove("bg-green-600");
    popup.classList.add("bg-red-600");
  }

  // Mostra com slide-in
  popup.classList.remove("hidden");
  setTimeout(() => {
    popup.classList.remove("translate-y-10", "opacity-0");
    popup.classList.add("translate-y-0", "opacity-100");
  }, 10);

  // Esconde após 3 segundos com animação reversa
  setTimeout(() => {
    popup.classList.remove("translate-y-0", "opacity-100");
    popup.classList.add("translate-y-10", "opacity-0");

    setTimeout(() => {
      popup.classList.add("hidden");
    }, 500); // Espera a animação terminar
  }, 3000);
}

// Obter utilizador autenticado de qualquer storage
function getUser() {
  const raw = localStorage.getItem("user") || sessionStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

// debounce p/ pesquisas
function debounce(fn, wait = 250) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

// emoji fallback de bandeira
function flagEmojiFromCCA2(code = "") {
  return code
    .toUpperCase()
    .replace(/./g, ch => String.fromCodePoint(127397 + ch.charCodeAt()));
}

/* =========================================================
   Auth: Registo, Login, Logout
========================================================= */

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
  if (!isValidEmail(email)) {
    showAlert("Email inválido.");
    return;
  }
  if (avatarFile && !avatarFile.name.toLowerCase().endsWith(".png")) {
    showAlert("Por favor seleciona uma imagem em formato .png");
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
    setTimeout(() => (window.location.href = "../sections/login.html"), 1500);
  } catch (err) {
    console.error("Erro no registo:", err);
    showAlert(err.message || "Erro ao registar.");
  }
}

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

    if (lembrar) localStorage.setItem("user", JSON.stringify(userData));
    else sessionStorage.setItem("user", JSON.stringify(userData));

    showAlert("Login realizado com sucesso!", "success");
    setTimeout(() => (window.location.href = "../index.html#ingest"), 2000);
  } catch (err) {
    console.error("Erro no login:", err);
    showAlert(err.message || "Erro ao autenticar.");
  }
}

function logout() {
  localStorage.removeItem("user");
  sessionStorage.removeItem("user");
  window.location.href = "../sections/login.html";
}

/* =========================================================
   Bootstrap + Modal País → Universidades
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  // --- estado sessão topo ---
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

  if (user?.email) {
    fetch(`http://localhost:5000/api/user/profile?email=${encodeURIComponent(user.email)}`)
      .then(res => {
        if (!res.ok) throw new Error("Sessão inválida");
        return res.json();
      })
      .then(() => {
        authButtons?.classList.add("hidden");
        logoutBtn?.classList.remove("hidden");
        input?.classList.remove("hidden");
      })
      .catch(() => {
        localStorage.removeItem("user");
        sessionStorage.removeItem("user");
        window.location.href = "../sections/login.html";
      });
  } else {
    authButtons?.classList.remove("hidden");
    logoutBtn?.classList.add("hidden");
    input?.classList.add("hidden");
  }

  // --- Modal País → Universidades ---
  const instInput   = document.getElementById("instituicao");
  const instModal   = document.getElementById("instModal");
  const modalClose  = document.getElementById("modalClose");
  const modalCancel = document.getElementById("modalCancel");
  const modalBack   = document.getElementById("modalBack");
  const modalTitle  = document.getElementById("modalTitle");
  const modalList   = document.getElementById("modalList");
  const modalSearch = document.getElementById("modalSearch");

  // fonte de verdade (dataset oficial HipoLabs)
  const HIPOLABS_DATASET_URL =
    "https://raw.githubusercontent.com/Hipo/university-domains-list/master/world_universities_and_domains.json";

  // estado do modal
  let countries = [];        // [{displayName, apiName, flag?, code?}]
  let allUnis = [];          // dataset completo (fallback local)
  let universities = [];     // resultados correntes
  let currentCountry = null; // objeto do país selecionado
  let view = "countries";    // "countries" | "universities"

  // abrir modal -> SEMPRE volta aos países
  instInput?.addEventListener("click", async () => {
    instModal.classList.remove("hidden");
    if (countries.length === 0) {
      modalList.innerHTML = "<p style='padding:1rem'>A carregar países...</p>";
      await loadCountries();
    }
    openCountriesView();
  });

  // fechar (botões/ESC/click fora) -> limpa p/ próxima abertura
  [modalClose, modalCancel].forEach(btn =>
    btn.addEventListener("click", () => {
      instModal.classList.add("hidden");
      openCountriesView();
    })
  );
  document.addEventListener("keydown", e => {
    if (!instModal.classList.contains("hidden") && e.key === "Escape") {
      instModal.classList.add("hidden");
      openCountriesView();
    }
  });
  instModal.addEventListener("click", e => {
    if (e.target === instModal) {
      instModal.classList.add("hidden");
      openCountriesView();
    }
  });

  // voltar
  modalBack.addEventListener("click", openCountriesView);

  // força vista Países
  function openCountriesView() {
    view = "countries";
    currentCountry = null;
    universities = [];
    modalTitle.textContent = "Escolhe um país";
    modalBack.disabled = true;
    modalSearch.value = "";
    renderCountries(countries);
    setTimeout(() => modalSearch.focus(), 10);
  }

  // carregar países do dataset oficial (e tentar enriquecer com flags)
  async function loadCountries() {
    try {
      const res = await fetch(HIPOLABS_DATASET_URL, { cache: "no-store" });
      const data = await res.json(); // array de universidades
      allUnis = Array.isArray(data) ? data : [];

      const set = new Set(allUnis.map(u => u.country).filter(Boolean));
      const names = Array.from(set).sort((a, b) =>
        a.localeCompare(b, "en", { sensitivity: "base" })
      );

      // criar objetos base sem flags
      countries = names.map(n => ({
        displayName: n,
        apiName: n,
        flag: null,
        code: ""
      }));

      // tentar enriquecer com REST Countries (não é crítico)
      try {
        const rc = await fetch("https://restcountries.com/v3.1/all?fields=name,cca2,flags")
          .then(r => r.json());
        const byName = new Map(
          rc.map(c => [c?.name?.common, { flag: c?.flags?.png || c?.flags?.svg, code: c?.cca2 }])
        );
        countries = countries.map(c => {
          const m = byName.get(c.apiName);
          return m ? { ...c, flag: m.flag || null, code: m.code || "" } : c;
        });
      } catch { /* se falhar, seguimos sem flags */ }

    } catch (e) {
      console.error(e);
      modalList.innerHTML = "<p style='padding:1rem;color:#b91c1c'>Erro ao carregar países.</p>";
    }
  }

  // render países
  function renderCountries(list) {
    modalList.innerHTML = "";
    if (!list || !list.length) {
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
          img.replaceWith(
            Object.assign(document.createElement("span"), {
              textContent: flagEmojiFromCCA2(c.code || ""),
              style: "font-size:18px;width:24px;display:inline-block;text-align:center;"
            })
          );
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
      item.onclick = choose;
      item.onkeydown = e => (e.key === "Enter" || e.key === " ") && choose();

      frag.appendChild(item);
    });
    modalList.appendChild(frag);
  }

  // selecionar país -> vista universidades (lazy: só pesquisa quando se escreve)
  async function selectCountry(countryObj) {
    view = "universities";
    currentCountry = countryObj;
    modalTitle.textContent = `Universidades em ${countryObj.displayName}`;
    modalBack.disabled = false;
    modalSearch.value = "";
    universities = [];

    // não puxamos a lista inteira (pode rebentar). instrução:
    modalList.innerHTML = `
      <p style="padding:1rem;color:#374151">
        Escreve <strong>pelo menos 2 letras</strong> para pesquisar universidades em
        <em>${countryObj.displayName}</em>.
      </p>`;
    setTimeout(() => modalSearch.focus(), 20);
  }

  // fetch filtrado (country + name). HTTPS para evitar mismatches.
  async function fetchUniversitiesFiltered(countryEn, term) {
    const qs = new URLSearchParams({ country: countryEn, name: term || "" });
    const url = `https://universities.hipolabs.com/search?${qs.toString()}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error("Falha ao obter universidades");
    return await res.json();
  }

  // fallback local: filtra dataset do GitHub
  function localFilterUniversities(countryEn, term) {
    const t = (term || "").toLowerCase();
    return allUnis.filter(
      u =>
        u.country === countryEn &&
        (!t || (u.name || "").toLowerCase().includes(t))
    );
  }

  // render universidades (com limite + "Carregar mais")
  function renderUniversities(list) {
    modalList.innerHTML = "";
    if (!list || !list.length) {
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
      item.textContent = u.name || "—";
      item.title = u.web_pages?.[0] || "";

      const choose = () => {
        document.getElementById("instituicao").value = u.name || "";
        instModal.classList.add("hidden");
        openCountriesView(); // prepara próxima abertura
      };

      item.onclick = choose;
      item.onkeydown = e => (e.key === "Enter" || e.key === " ") && choose();

      frag.appendChild(item);
    });

    modalList.appendChild(frag);

    if (list.length > take) {
      const more = document.createElement("button");
      more.className = "btn-secondary";
      more.style.margin = "0.75rem";
      more.textContent = `Carregar mais (${list.length - take})`;
      more.onclick = () => {
        renderUniversities(list.slice(take));
      };
      modalList.appendChild(more);
    }
  }

  // pesquisa no modal (usa view atual)
  const handleSearch = debounce(async () => {
    const term = (modalSearch.value || "").trim();

    if (view === "countries") {
      const t = term.toLowerCase();
      const filtered = countries.filter(c =>
        c.displayName.toLowerCase().includes(t)
      );
      renderCountries(filtered);
      return;
    }

    // universidades
    if (!currentCountry) return;
    if (term.length < 2) {
      modalList.innerHTML = `
        <p style="padding:1rem;color:#374151">
          Escreve <strong>pelo menos 2 letras</strong> para pesquisar universidades.
        </p>`;
      return;
    }

    const countryApi = currentCountry.apiName;
    modalList.innerHTML = "<p style='padding:1rem'>A procurar…</p>";
    try {
      const list = await fetchUniversitiesFiltered(countryApi, term);
      if (Array.isArray(list) && list.length) {
        universities = list;
        renderUniversities(universities);
      } else {
        // fallback local
        universities = localFilterUniversities(countryApi, term);
        renderUniversities(universities);
      }
    } catch (e) {
      console.error(e);
      // fallback local em caso de erro de rede
      universities = localFilterUniversities(countryApi, term);
      renderUniversities(universities);
    }
  }, 300);

  modalSearch.addEventListener("input", handleSearch);


    const funcaoSelect = document.getElementById("funcaoSelect");
  if (!funcaoSelect) return;

  const trigger = funcaoSelect.querySelector(".select-trigger");
  const menu    = funcaoSelect.querySelector(".select-menu");
  const hidden  = funcaoSelect.querySelector("input[type=hidden]");
  const text    = funcaoSelect.querySelector(".select-text");

  // Abre/fecha menu
  trigger.addEventListener("click", () => {
    menu.classList.toggle("hidden");
    funcaoSelect.classList.toggle("open");
  });

  // Fecha ao clicar fora
  document.addEventListener("click", e => {
    if (!funcaoSelect.contains(e.target)) {
      menu.classList.add("hidden");
      funcaoSelect.classList.remove("open");
    }
  });

  // Escolher opção
  menu.querySelectorAll(".option").forEach(opt => {
    opt.addEventListener("click", () => {
      const val = opt.dataset.value;
      hidden.value = val;
      text.textContent = val;
      funcaoSelect.classList.add("has-value");
      menu.classList.add("hidden");
      funcaoSelect.classList.remove("open");
    });
  });
});
