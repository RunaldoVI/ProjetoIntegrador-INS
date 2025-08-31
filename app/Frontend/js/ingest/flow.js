window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  const { state, session, apiClient, previewRenderer, previewActions, logsModal } = ns;

  // ===== helpers =====
  function getCurrentUserSafe() {
    try {
      if (typeof getUser === "function") return getUser();
      const raw = localStorage.getItem("user") || sessionStorage.getItem("user");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }

  async function logHistorySafe({ email, nome_pdf, pdfFile = null }) {
    try {
      if (apiClient && typeof apiClient.logHistory === "function") {
        return await apiClient.logHistory({ email, nome_pdf, pdfFile });
      }
      const fd = new FormData();
      fd.append("email", email);
      if (pdfFile) fd.append("pdf", pdfFile);
      else if (nome_pdf) fd.append("nome_pdf", nome_pdf);
      await fetch("http://localhost:5000/api/user/upload_pdf", { method: "POST", body: fd });
    } catch (e) {
      console.warn("[history] falha a registar:", e);
    }
  }

  // ===== estilos modal feedback =====
  function ensureFeedbackModalStyles() {
    if (document.getElementById("feedback-modal-styles")) return;
    const css = `
    .fbk-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.55);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:50}
    .fbk-panel{width:100%;max-width:640px;background:var(--darkCard,#262b3d);border:1px solid rgba(255,255,255,.1);border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.5);color:#fff;transform:translateY(8px) scale(.98);opacity:0;transition:.16s ease}
    .fbk-panel.fbk-in{transform:translateY(0) scale(1);opacity:1}
    .fbk-header{display:flex;align-items:center;gap:.6rem;padding:16px 18px;border-bottom:1px solid rgba(255,255,255,.08)}
    .fbk-title{margin:0;font-size:1.05rem;font-weight:700}
    .fbk-icon{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:rgba(239,68,68,.18);border:1px solid rgba(239,68,68,.25)}
    .fbk-close{margin-left:auto;width:36px;height:36px;border-radius:10px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.06);color:#fff}
    .fbk-close:hover{background:rgba(255,255,255,.1)}
    .fbk-body{padding:16px 18px}
    .fbk-textarea{width:100%;min-height:150px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#fff;padding:12px;resize:vertical;outline:none}
    .fbk-textarea:focus{border-color:rgba(139,155,255,.5);box-shadow:0 0 0 3px rgba(139,155,255,.12)}
    .fbk-hint{margin-top:8px;font-size:.85rem;color:rgba(255,255,255,.65);display:flex;justify-content:space-between;gap:8px}
    .fbk-footer{display:flex;justify-content:flex-end;gap:10px;padding:16px 18px;border-top:1px solid rgba(255,255,255,.08)}
    .fbk-btn{display:inline-flex;align-items:center;gap:.5rem;border-radius:12px;border:1px solid rgba(255,255,255,.1);padding:.6rem 1rem;color:#fff;background:rgba(255,255,255,.06);transition:.15s}
    .fbk-btn:hover{background:rgba(255,255,255,.1)}
    .fbk-btn-green{background:#22c55e;border-color:transparent}
    .fbk-btn-green:hover{filter:brightness(1.05)}
    .fbk-btn-red{background:#ef4444;border-color:transparent}
    .fbk-btn-red:hover{filter:brightness(1.05)}
    .fbk-counter{opacity:.75}
    @media (prefers-reduced-motion: reduce){.fbk-panel{transition:none}}
    `;
    const style = document.createElement("style");
    style.id = "feedback-modal-styles";
    style.textContent = css;
    document.head.appendChild(style);
  }

  function trapFocus(modal) {
    const selectors = 'button,[href],input,textarea,select,[tabindex]:not([tabindex="-1"])';
    const focusables = Array.from(modal.querySelectorAll(selectors)).filter(el => !el.disabled && el.offsetParent !== null);
    const first = focusables[0], last = focusables[focusables.length - 1];
    function handle(e){
      if (e.key !== 'Tab') return;
      if (e.shiftKey && document.activeElement === first){ last.focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === last){ first.focus(); e.preventDefault(); }
    }
    modal.addEventListener('keydown', handle);
    return () => modal.removeEventListener('keydown', handle);
  }

  async function loadPreviewBlock(questionnaire, ident = null, file = null) {
    const payload = await apiClient.getPreviewItem(questionnaire, { ident, file });
    previewRenderer.render(payload, loadPreviewBlock);
    session.set("fromPreview", "true");
    session.set("previewQuestionario", payload.questionario || "");
    mountPreviewActions();
  }

  function mountPreviewActions() {
    // limpa instâncias antigas
    document.getElementById("output")
      ?.querySelectorAll(".continuar-btn, .naogosto-btn, .actions-wrap")
      .forEach((el) => el.remove());

    previewActions.mount(
      // onContinue — (só aqui grava histórico no modo preview)
      async () => {
        const fromPreview = session.get("fromPreview") === "true";
        const questionnaire = session.get("previewQuestionario") || state.nav.questionnaire;

        if (!fromPreview || !questionnaire) {
          showToast("Sem contexto de preview — a continuar pelo modo automático…", "warning");
          const file = window.IngestHelpers.ui.recreateFileFromSession();
          if (!file) return showToast("Erro: ficheiro PDF não encontrado.", "error");
          return analyzePdf(file, "automatico");
        }

        const btn = document.querySelector(".continuar-btn");
        const dislike = document.querySelector(".naogosto-btn");
        const prevText = btn.textContent;
        btn.disabled = true; dislike.disabled = true; btn.textContent = "A finalizar...";

        try {
          const data = await apiClient.finalize(questionnaire);

          // === HISTÓRICO (preview → continuar) ===
          try {
            const user = getCurrentUserSafe();
            const nomePdf = session.get("pdfName");
            if (user?.email && nomePdf) {
              await logHistorySafe({ email: user.email, nome_pdf: nomePdf });
            } else {
              console.warn("[history][preview→continuar] faltam dados (email/nome_pdf)");
            }
          } catch (e) { console.warn("[history][preview→continuar] falha:", e); }

          const out = document.getElementById("output");
          const msg = data.mensagem || "Blocos consolidados a partir do preview.";
          const excelReady = data.excel === true || !!data.download_excel;
          const downloadUrl = data.download_excel || "http://localhost:5000/download-excel";
          const filesCount = (data.files_count ?? data.total ?? data.total_json ?? "—");
          const duration   = (data.duration_human ?? data.duration ?? data.tempo ?? "—");
          const warnings = Array.isArray(data.warnings) ? data.warnings.length : (data.warnings_count || 0);

          out.innerHTML = `
            <div class="mt-4 p-0 rounded-xl overflow-hidden border border-white/10 bg-[#212433]">
              <div class="bg-gradient-to-r from-green-600/20 to-emerald-600/20 px-6 py-5 flex items-center gap-3">
                <div class="relative w-9 h-9 rounded-full bg-green-600/30 flex items-center justify-center">
                  <svg class="w-5 h-5 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20 6L9 17l-5-5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  <span class="absolute inset-0 rounded-full ring-2 ring-green-400/40 animate-ping"></span>
                </div>
                <div><h3 class="text-lg font-semibold text-blue-400">Resultado da Consolidação</h3>
                  <p class="text-sm text-white/80">${msg}</p></div>
              </div>
              <div class="px-6 py-5">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div class="rounded-lg bg-white/5 px-4 py-3"><div class="text-xs uppercase tracking-wide text-white/60">Ficheiros</div><div class="text-xl font-bold text-white">${filesCount}</div></div>
                  <div class="rounded-lg bg-white/5 px-4 py-3"><div class="text-xs uppercase tracking-wide text-white/60">Duração</div><div class="text-xl font-bold text-white">${duration}</div></div>
                  <div class="rounded-lg bg-white/5 px-4 py-3"><div class="text-xs uppercase tracking-wide text-white/60">Avisos</div><div class="text-xl font-bold ${warnings ? "text-amber-300" : "text-white"}">${warnings}</div></div>
                </div>
                ${Array.isArray(data.warnings) && data.warnings.length ? `
                  <details class="mt-4 rounded-lg bg-[#1b1e2a] px-4 py-3">
                    <summary class="cursor-pointer text-sm text-white/90">Ver avisos (${data.warnings.length})</summary>
                    <ul class="mt-2 list-disc pl-5 text-sm text-white/70">${data.warnings.map(w => `<li>${String(w)}</li>`).join("")}</ul>
                  </details>` : ""}
                <div class="mt-5 flex flex-wrap items-center gap-3 justify-center">
                  ${excelReady ? `<a href="${downloadUrl}" download class="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium shadow"><span>⬇️</span> Descarregar Excel Gerado</a>`
                                : `<button disabled class="px-5 py-2 rounded-lg bg-gray-600 text-white opacity-60 cursor-not-allowed">Excel indisponível</button>`}
                  <button class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white" id="verLogsBtn">Ver logs</button>
                  <button class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white" id="copiarResumoBtn">Copiar resumo</button>
                </div>
              </div>
            </div>`;

          document.getElementById("copiarResumoBtn")?.addEventListener("click", async () => {
            const resumo = `Consolidação: ${filesCount} ficheiros • ${duration} • avisos: ${warnings}`;
            try { await navigator.clipboard.writeText(resumo); showToast("Resumo copiado!","success"); }
            catch { showToast("Não foi possível copiar.","error"); }
          });
          document.getElementById("verLogsBtn")?.addEventListener("click", logsModal.open);

          session.del("fromPreview");
          session.del("previewQuestionario");
          showToast("Consolidação concluída com sucesso!", "success");
        } catch (err) {
          console.error(err);
          showToast("Erro ao consolidar a partir do preview.", "error");
          const btn = document.querySelector(".continuar-btn");
          const dislike = document.querySelector(".naogosto-btn");
          if (btn && dislike) { btn.disabled = false; dislike.disabled = false; btn.textContent = prevText; }
        }
      },

      // onDislike (modal de instruções)
      () => {
        ensureFeedbackModalStyles();
        const id = "feedbackModal";
        let modal = document.getElementById(id);
        if (!modal) {
          modal = document.createElement("div");
          modal.id = id;
          modal.className = "fbk-backdrop hidden";
          modal.innerHTML = `
            <div class="fbk-panel" role="dialog" aria-modal="true" aria-labelledby="fbk-title">
              <div class="fbk-header">
                <div class="fbk-icon">✏️</div>
                <h3 id="fbk-title" class="fbk-title">Adicionar instruções personalizadas</h3>
                <button id="fbkClose" class="fbk-close" aria-label="Fechar">
                  <i class="fas fa-times"></i>
                </button>
              </div>
              <div class="fbk-body">
                <textarea id="fbkTextarea" class="fbk-textarea" placeholder="Explica ao modelo o que te incomodou e como queres que responda (ex.: sem caixas, mais conciso, etc.)"></textarea>
                <div class="fbk-hint">
                  <span>Dica: <b>Ctrl + Enter</b> para enviar</span>
                  <span class="fbk-counter" id="fbkCounter">0 / 500</span>
                </div>
              </div>
              <div class="fbk-footer">
                <button id="fbkCancel" class="fbk-btn fbk-btn-red">Cancelar</button>
                <button id="fbkSave" class="fbk-btn fbk-btn-green">Usar estas instruções</button>
              </div>
            </div>`;
          document.body.appendChild(modal);
        }

        const panel = modal.querySelector(".fbk-panel");
        const textarea = modal.querySelector("#fbkTextarea");
        const btnSave = modal.querySelector("#fbkSave");
        const btnCancel = modal.querySelector("#fbkCancel");
        const btnClose = modal.querySelector("#fbkClose");
        const counter = modal.querySelector("#fbkCounter");

        // mostrar
        modal.classList.remove("hidden");
        requestAnimationFrame(() => panel.classList.add("fbk-in"));
        document.body.style.overflow = "hidden";
        textarea.value = "";
        textarea.focus();
        counter.textContent = "0 / 500";

        // contador + limite
        textarea.oninput = () => {
          if (textarea.value.length > 500) textarea.value = textarea.value.slice(0,500);
          counter.textContent = `${textarea.value.length} / 500`;
        };

        // focus trap
        const untrap = trapFocus(panel);

        // fechar helpers
        const closeModal = () => {
          panel.classList.remove("fbk-in");
          setTimeout(() => modal.classList.add("hidden"), 120);
          document.body.style.overflow = "";
          document.removeEventListener("keydown", onKey);
          modal.removeEventListener("click", onBackdrop);
          untrap();
        };
        const onBackdrop = (e) => { if (e.target === modal) closeModal(); };
        const onKey = (e) => {
          if (e.key === "Escape") closeModal();
          if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "enter") btnSave.click();
        };

        modal.addEventListener("click", onBackdrop, { once:false });
        document.addEventListener("keydown", onKey);

        btnCancel.onclick = btnClose.onclick = closeModal;

        btnSave.onclick = async () => {
          const text = textarea.value.trim();
          if (!text) return showToast("Por favor escreve algo primeiro.", "warning");

          btnSave.disabled = true;
          btnSave.textContent = "A reenviar...";

          try {
            const questionnaire = session.get("previewQuestionario") || state.nav.questionnaire;
            const ident = state.nav.ident;
            const file  = state.nav.file;

            if (!questionnaire || (!ident && !file)) {
              showToast("Sem bloco selecionado para reprocessar.", "error");
              return;
            }

            const data = await apiClient.reprocessItem(questionnaire, { ident, file, instructions: text });
            previewRenderer.render(data, loadPreviewBlock);
            showToast("Instruções aplicadas e bloco reprocessado.", "success");
          } catch (err) {
            console.error(err);
            showToast("Falha ao reprocessar: " + (err?.message || err), "error");
          } finally {
            closeModal();
            btnSave.disabled = false;
            btnSave.textContent = "Usar estas instruções";
          }
        };
      }
    );
  }

  async function analyzePdf(file, forcedMode = null) {
    state.isAnalyzing = true;
    const output = document.getElementById("output");
    const button = document.getElementById("analisarBtn");
    if (!file || !button) return;

    // guarda o nome do ficheiro para usar depois no "Continuar" (preview)
    session.set("pdfName", file?.name || session.get("pdfName") || "");
    const modeNow = (forcedMode || state.processingMode);
    PDF_Keeper.start({ pdfName: file?.name, mode: modeNow });
    button.disabled = true;
    button.textContent = "Analisando...";

    const loader = document.createElement("div");
    loader.className = "mt-6 text-accent flex items-center gap-2";
    loader.innerHTML = `<svg class="animate-spin h-5 w-5 text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4"></path></svg> A analisar o PDF...`;
    output.appendChild(loader);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("modo", forcedMode || state.processingMode);

    try {
      // === HISTÓRICO (automático) — logo ao iniciar a análise
      const modeNow = (forcedMode || state.processingMode);
      if (modeNow !== "preview") {
        try {
          const user = getCurrentUserSafe();
          const nomePdf = file?.name || session.get("pdfName");
          if (user?.email && nomePdf) {
            await logHistorySafe({ email: user.email, nome_pdf: nomePdf });
          } else {
            console.warn("[history][automatico] faltam dados (email/nome_pdf)");
          }
        } catch (e) { console.warn("[history][automatico] falha:", e); }
      }

      const data = await apiClient.upload(formData);
      loader.remove();

      if ((forcedMode || state.processingMode) === "preview") {
        // PREVIEW: não gravar histórico aqui
        if (data && data.item && data.ident && data.questionario) {
          previewRenderer.render(data, loadPreviewBlock);
          session.set("fromPreview", "true");
          session.set("previewQuestionario", data.questionario || "");
          mountPreviewActions();
        } else {
          showToast("Preview inválido: resposta inesperada da API.", "error");
        }
      } else {
        // AUTOMÁTICO: UI de resultado
        const excelUrl = "http://localhost:5000/download-excel";
        output.innerHTML = `
          <div class="mt-4 p-0 rounded-xl overflow-hidden border border-white/10 bg-[#212433]">
            <div class="bg-gradient-to-r from-blue-600/20 to-indigo-600/20 px-6 py-5 flex items-center gap-3">
              <div class="w-9 h-9 rounded-full bg-blue-600/30 flex items-center justify-center">
                <svg class="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M12 8v8m-4-4h8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </div>
              <div><h3 class="text-lg font-semibold text-blue-400">Resultado da Análise</h3>
                <p class="text-sm text-white/80">${data.mensagem || "Análise concluída."}</p></div>
            </div>
            <div class="px-6 py-5">
              <div class="flex flex-wrap items-center gap-3 justify-center">
                <a href="${excelUrl}" download class="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium shadow">⬇️ Descarregar Excel Gerado</a>
                <button class="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white" id="verResumoBtn">Ver resumo</button>
              </div>
            </div>
          </div>`;
        document.getElementById("verResumoBtn")?.addEventListener("click", () => {
          showToast("Em breve: resumo detalhado da execução.","info");
        });
      }

      showToast("Análise concluída com sucesso!", "success");
    } finally {
      if (button) { button.disabled = false; button.textContent = "Analisar PDF"; }
      state.isAnalyzing = false;
    }
  }
  
  ns.flow = { loadPreviewBlock, mountPreviewActions, analyzePdf };
})(window.IngestHelpers);
