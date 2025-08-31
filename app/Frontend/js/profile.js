// profile.js

// Lê user de qualquer storage
function readUserAnyStorage() {
  const ls = localStorage.getItem("user");
  const ss = sessionStorage.getItem("user");
  try { return ls ? JSON.parse(ls) : (ss ? JSON.parse(ss) : null); }
  catch { return null; }
}


// ---- Função principal ----
function loadProfile() {
  // usa getUser() do auth.js se existir; senão fallback
  const user = (typeof getUser === "function") ? getUser() : readUserAnyStorage();
  console.log("[profile] user lido:", user);

  if (!user || !user.email) {
    console.warn("[profile] sem sessão; redirecionar para login");
    window.location.href = "../sections/login.html";
    return;
  }

  // Buscar dados do perfil
  fetch("http://localhost:5000/api/user/profile?email=" + encodeURIComponent(user.email))
    .then((res) => {
      if (!res.ok) throw new Error("Erro ao carregar perfil");
      return res.json();
    })
    .then((dados) => {
      // Preencher UI
      const el = (id) => document.getElementById(id);
      const userName = el("user-name");
      const userInfo = el("user-info");
      const pNome    = el("profile-nome");
      const pEmail   = el("profile-email");
      const pFuncao  = el("profile-funcao");
      const pInst    = el("profile-inst");
      const avatarImg = el("user-avatar");

      if (userName) userName.textContent = dados.nome || "—";
      if (userInfo) userInfo.textContent = "Utilizador registado com o email " + (dados.email || "—");
      if (pNome)   pNome.textContent   = dados.nome || "—";
      if (pEmail)  pEmail.textContent  = dados.email || "—";
      if (pFuncao) pFuncao.textContent = dados.funcao || "—";
      if (pInst)   pInst.textContent   = dados.instituicao || "—";

      if (avatarImg) {
        avatarImg.src = "http://localhost:5000/uploads/avatars/" + (dados.avatar || "default.png");
        avatarImg.onerror = () => { avatarImg.src = "http://localhost:5000/uploads/avatars/default.png"; };
      }

      // Atualizar na MESMA storage onde estava
      const inSession = sessionStorage.getItem("user") !== null && !localStorage.getItem("user");
      const raw = JSON.stringify(dados);
      if (inSession) sessionStorage.setItem("user", raw);
      else localStorage.setItem("user", raw);

      carregarHistoricoPDFs();
      ligarModalEdicao(); // liga os listeners do modal
    })
    .catch((err) => {
      console.error("Erro ao carregar perfil:", err);
    });
}

// ---- Modal Editar Perfil ----
function ligarModalEdicao() {
  const byId = (id) => document.getElementById(id);

  const btnEditar    = byId("btnEditarPerfil");
  const modal        = byId("editModal");
  const modalContent = byId("editModalContent");
  const btnCancelar  = byId("btnCancelar");
  const btnGuardar   = byId("btnGuardar");
  const editAvatar   = byId("editAvatar");

  if (!btnEditar || !modal || !modalContent) return;

  let avatarBase64 = "";

  btnEditar.addEventListener("click", () => {
    const u = readUserAnyStorage();
    if (u) {
      const preview = byId("avatarPreview");
      const eNome   = byId("editNome");
      const eEmail  = byId("editEmail");
      const eFuncao = byId("editFuncao");
      const eInst   = byId("editInstituicao");

      if (eNome)   eNome.value   = u.nome || "";
      if (eEmail)  eEmail.value  = u.email || "";
      if (eFuncao) eFuncao.value = u.funcao || "";
      if (eInst)   eInst.value   = u.instituicao || "";
      if (preview) preview.src   = "http://localhost:5000/uploads/avatars/" + (u.avatar || "default.png");
    }
    
    setupEditFuncaoSelect();
    setupEditInstituicaoModal();

    modal.classList.remove("hidden");
    modal.classList.add("bg-opacity-60");
    setTimeout(() => {
      modalContent.classList.add("scale-100", "opacity-100");
      modalContent.classList.remove("scale-95", "opacity-0");
    }, 10);
  });

  function fecharModal() {
    modal.classList.remove("bg-opacity-60");
    modalContent.classList.remove("scale-100", "opacity-100");
    modalContent.classList.add("scale-95", "opacity-0");
    setTimeout(() => modal.classList.add("hidden"), 300);
  }

  if (btnCancelar) btnCancelar.addEventListener("click", fecharModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) fecharModal(); });

  if (editAvatar) {
    editAvatar.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (!["image/jpeg", "image/png"].includes(file.type)) { alert("Apenas JPG ou PNG."); e.target.value = ""; return; }
      if (file.size > 3 * 1024 * 1024) { alert("Máx. 3MB."); e.target.value = ""; return; }
      const reader = new FileReader();
      reader.onload = function(ev) {
        avatarBase64 = ev.target.result;
        const preview = document.getElementById("avatarPreview");
        if (preview) preview.src = avatarBase64;
      };
      reader.readAsDataURL(file);
    });
  }

if (btnGuardar) {
  btnGuardar.addEventListener("click", async () => {
    const currentUser = readUserAnyStorage(); // vem da sessão
    const emailOriginal = currentUser?.email || ""; // usamos este no WHERE

    const nome  = (document.getElementById("editNome")  || {}).value?.trim() || "";
    const emailNovo = (document.getElementById("editEmail") || {}).value?.trim() || ""; // só para mostrar/GET
    const funcao = (document.getElementById("editFuncao") || {}).value?.trim() || "";
    const instituicao = (document.getElementById("editInstituicao") || {}).value?.trim() || "";
    const avatarFile = document.getElementById("editAvatar")?.files?.[0];

    const formData = new FormData();
    formData.append("email", emailOriginal);          // <- importante: identifica o registo
    if (nome)        formData.append("nome", nome);
    if (funcao)      formData.append("funcao", funcao);
    if (instituicao) formData.append("instituicao", instituicao);
    if (avatarFile)  formData.append("avatar", avatarFile);

    // (Opcional) se quiseres preparar "trocar email" no futuro, manda também:
    // if (emailNovo && emailNovo !== emailOriginal) formData.append("new_email", emailNovo);

    if (![ "nome","funcao","instituicao","avatar" ].some(k => formData.has(k))) {
      console.log("Nenhum campo foi alterado.");
      return;
    }

    try {
      const putRes = await fetch("http://localhost:5000/api/user/profile", {
        method: "PUT",
        body: formData
      });
      if (!putRes.ok) throw new Error("Erro ao guardar perfil");

      // Depois do PUT, volta a ler o perfil (usa o email original)
      const getRes = await fetch("http://localhost:5000/api/user/profile?email=" + encodeURIComponent(emailOriginal));
      if (!getRes.ok) throw new Error("Erro ao ler perfil atualizado");
      const updated = await getRes.json();

      // Atualiza na MESMA storage onde estava
      const inSession = sessionStorage.getItem("user") !== null && !localStorage.getItem("user");
      const raw = JSON.stringify(updated);
      if (inSession) sessionStorage.setItem("user", raw);
      else localStorage.setItem("user", raw);

      // Atualiza UI sem recarregar
      document.getElementById("user-name").textContent = updated.nome || "—";
      document.getElementById("user-info").textContent = "Utilizador registado com o email " + (updated.email || "—");
      document.getElementById("profile-nome").textContent = updated.nome || "—";
      document.getElementById("profile-email").textContent = updated.email || "—";
      document.getElementById("profile-funcao").textContent = updated.funcao || "—";
      document.getElementById("profile-inst").textContent = updated.instituicao || "—";
      const avatarImg = document.getElementById("user-avatar");
      if (avatarImg) {
        avatarImg.src = "http://localhost:5000/uploads/avatars/" + (updated.avatar || "default.png");
        avatarImg.onerror = () => { avatarImg.src = "http://localhost:5000/uploads/avatars/default.png"; };
      }

      console.log("Perfil atualizado com sucesso:", updated);
      fecharModal();

      // se quiseres mesmo recarregar a página, só depois de teres o user válido guardado:
      // location.reload();
    } catch (err) {
      console.error("Erro ao guardar perfil:", err);
    }
  });
}
}

// ---- Histórico de PDFs ----
function carregarHistoricoPDFs() {
  const user = readUserAnyStorage();
  const lista = document.getElementById("pdf-history");
  if (!lista) return;

  if (!user || !user.email) {
    lista.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
    return;
  }

  fetch("http://localhost:5000/api/user/historico?email=" + encodeURIComponent(user.email))
    .then(res => res.json())
    .then(data => {
      if (data.historico && data.historico.length > 0) {
        const items = data.historico.map(item => `
          <li class="flex items-center justify-between">
            <span>PDF: ${item.nome}</span>
            <span class="text-xs text-gray-500">${item.data}</span>
          </li>
        `).join("");
        lista.innerHTML = items;
      } else {
        lista.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
      }
    })
    .catch(err => {
      console.error("Erro ao carregar histórico de PDFs:", err);
      lista.innerHTML = "<li>Erro ao carregar histórico.</li>";
    });
}

// Mostrar/ocultar password (se usado no modal)
function togglePassword() {
  const passwordField = document.getElementById("editPassword");
  const passwordIcon = document.getElementById("togglePasswordIcon");
  if (!passwordField || !passwordIcon) return;
  if (passwordField.type === "password") {
    passwordField.type = "text";
    passwordIcon.classList.remove("fa-eye");
    passwordIcon.classList.add("fa-eye-slash");
  } else {
    passwordField.type = "password";
    passwordIcon.classList.remove("fa-eye-slash");
    passwordIcon.classList.add("fa-eye");
  }
}

// ===== Dropdown "Função" (edição) =====
function setupEditFuncaoSelect() {
  const funcaoSelectRoot = document.getElementById("editFuncaoSelect");
  if (!funcaoSelectRoot) return;

  const trigger = funcaoSelectRoot.querySelector(".select-trigger");
  const menu = funcaoSelectRoot.querySelector(".select-menu");
  const hiddenInput = document.getElementById("editFuncao");
  const visibleText = funcaoSelectRoot.querySelector(".select-text");

  trigger?.addEventListener("click", () => {
    menu?.classList.toggle("hidden");
    funcaoSelectRoot.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (!funcaoSelectRoot.contains(e.target)) {
      menu?.classList.add("hidden");
      funcaoSelectRoot.classList.remove("open");
    }
  });

  menu?.querySelectorAll(".option").forEach((opt) => {
    opt.addEventListener("click", () => {
      const value = opt.getAttribute("data-value") || "";
      if (hiddenInput) hiddenInput.value = value;
      if (visibleText) visibleText.textContent = value;
      funcaoSelectRoot.classList.add("has-value");
      menu.classList.add("hidden");
      funcaoSelectRoot.classList.remove("open");
    });
  });

  // Pré-preencher
  const u = readUserAnyStorage();
  if (u?.funcao) {
    if (hiddenInput) hiddenInput.value = u.funcao;
    if (visibleText) visibleText.textContent = u.funcao;
    funcaoSelectRoot.classList.add("has-value");
  }
}

// ===== Modal "Instituição" (edição) =====
function setupEditInstituicaoModal() {
  const inputInstituicao = document.getElementById("editInstituicao");
  const modal = document.getElementById("instModal");
  const btnClose = document.getElementById("modalClose");
  const btnCancel = document.getElementById("modalCancel");
  const btnBack = document.getElementById("modalBack");
  const titleEl = document.getElementById("modalTitle");
  const listEl = document.getElementById("modalList");
  const searchEl = document.getElementById("modalSearch");
  if (!(inputInstituicao && modal && btnBack && titleEl && listEl && searchEl)) return;

  const DATASET_URL = "https://raw.githubusercontent.com/Hipo/university-domains-list/master/world_universities_and_domains.json";
  let countries = [], allUnis = [], selectedCountry = null, view = "countries";

  const on = (el, ev, fn) => el && el.addEventListener(ev, fn);
  const flagEmoji = (code="") => code.toUpperCase().replace(/./g, ch => String.fromCodePoint(127397 + ch.charCodeAt()));

  // abrir
  on(inputInstituicao, "click", async () => {
    modal.classList.remove("hidden");
    if (!countries.length) {
      listEl.innerHTML = "<p style='padding:1rem'>A carregar países...</p>";
      try {
        const r = await fetch(DATASET_URL, { cache:"no-store" });
        const data = await r.json();
        allUnis = Array.isArray(data) ? data : [];
        const set = new Set(allUnis.map(u=>u.country).filter(Boolean));
        countries = Array.from(set).sort((a,b)=>a.localeCompare(b,"en",{sensitivity:"base"}))
          .map(n => ({ name:n, code2:"", flag:null }));
        try {
          const rc = await fetch("https://restcountries.com/v3.1/all?fields=name,cca2,flags").then(r=>r.json());
          const map = new Map(rc.map(c => [c?.name?.common, { code2:c?.cca2||"", flag:(c?.flags?.png||c?.flags?.svg)||null }]));
          countries = countries.map(c => map.get(c.name) ? { ...c, ...map.get(c.name) } : c);
        } catch {}
      } catch { listEl.innerHTML = "<p style='padding:1rem;color:#b91c1c'>Erro ao carregar países.</p>"; }
    }
    openCountries();
    setTimeout(()=>searchEl.focus(), 20);
  });

  // fechar
  [btnClose, btnCancel].forEach(b => on(b, "click", () => { modal.classList.add("hidden"); openCountries(); }));
  on(modal, "click", e => { if (e.target === modal) { modal.classList.add("hidden"); openCountries(); }});
  on(btnBack, "click", openCountries);

  function renderCountries(list){
    listEl.innerHTML = "";
    if (!list?.length){ listEl.innerHTML = "<p style='padding:1rem'>Nenhum país encontrado.</p>"; return; }
    const frag = document.createDocumentFragment();
    list.forEach(c=>{
      const item = document.createElement("div");
      item.className = "modal__item"; item.tabIndex = 0; item.role = "button";
      const flag = document.createElement("span");
      if (c.flag){ const img=document.createElement("img"); img.className="flag"; img.src=c.flag; img.alt=c.name;
        img.onerror=()=>{ flag.textContent = flagEmoji(c.code2||""); img.replaceWith(flag); }; item.appendChild(img);
      } else { flag.textContent = flagEmoji(c.code2||""); flag.style="font-size:18px;width:24px;display:inline-block;text-align:center;"; item.appendChild(flag); }
      const label = document.createElement("span"); label.textContent = " " + c.name; item.appendChild(label);
      const choose = ()=>selectCountry(c);
      item.addEventListener("click", choose);
      item.addEventListener("keydown", e => { if (e.key==="Enter"||e.key===" ") choose(); });
      frag.appendChild(item);
    });
    listEl.appendChild(frag);
  }

  function renderUniversities(list){
    listEl.innerHTML = "";
    if (!list?.length){ listEl.innerHTML = "<p style='padding:1rem'>Nenhuma universidade encontrada.</p>"; return; }
    const frag = document.createDocumentFragment();
    list.slice(0,300).forEach(u=>{
      const item = document.createElement("div");
      item.className="modal__item"; item.tabIndex=0; item.role="button"; item.textContent = u.name || "-";
      item.title = (u.web_pages && u.web_pages[0]) || "";
      const choose = ()=>{ inputInstituicao.value = u.name || ""; modal.classList.add("hidden"); openCountries(); };
      item.addEventListener("click", choose);
      item.addEventListener("keydown", e => { if (e.key==="Enter"||e.key===" ") choose(); });
      frag.appendChild(item);
    });
    listEl.appendChild(frag);
  }

  function openCountries(){
    view = "countries"; selectedCountry = null; searchEl.value = "";
    titleEl.textContent = "Escolha um país"; btnBack.disabled = true; renderCountries(countries);
  }
  function selectCountry(c){
    view = "universities"; selectedCountry = c; searchEl.value = "";
    titleEl.textContent = "Universidades em " + c.name; btnBack.disabled = false;
    listEl.innerHTML = "<p style='padding:1rem;color:#e5e7eb;'>Escreva pelo menos 2 letras para pesquisar universidades.</p>";
  }

  const debounce = (fn, wait=300)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), wait); }; };
  const onSearch = debounce(async ()=>{
    const term = (searchEl.value||"").trim();
    if (view==="countries"){
      const t = term.toLowerCase();
      return renderCountries(countries.filter(c=>c.name.toLowerCase().includes(t)));
    }
    if (!selectedCountry) return;
    if (term.length < 2){
      listEl.innerHTML = "<p style='padding:1rem;color:#374151'>Escreva pelo menos 2 letras para pesquisar universidades.</p>";
      return;
    }
    listEl.innerHTML = "<p style='padding:1rem'>A procurar...</p>";
    try{
      const qs = new URLSearchParams({ country: selectedCountry.name, name: term });
      const r = await fetch("https://universities.hipolabs.com/search?"+qs.toString(), { cache:"no-store" });
      const api = await r.json();
      renderUniversities(Array.isArray(api) && api.length ? api : allUnis.filter(u=>u.country===selectedCountry.name && (u.name||"").toLowerCase().includes(term.toLowerCase())));
    }catch{
      renderUniversities(allUnis.filter(u=>u.country===selectedCountry.name && (u.name||"").toLowerCase().includes(term.toLowerCase())));
    }
  }, 300);
  searchEl.addEventListener("input", onSearch);
}

// Arranque
document.addEventListener("DOMContentLoaded", () => {
  console.log("[profile] localStorage:", localStorage.getItem("user"));
  console.log("[profile] sessionStorage:", sessionStorage.getItem("user"));
  setTimeout(() => {}, 3500);
  loadProfile();
});
