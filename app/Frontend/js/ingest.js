function loadIngest() {
  console.log("ingest.js carregado com sucesso!");

  let modoAtual = localStorage.getItem("modo") || "automatico";
  let currentPdfFile = null;
  let analyzing = false;

  // estado navegação
  let navState = { questionario: null, ident: null, file: null };

  function renderPreviewBlock(payload) {
    // payload vem do backend
    navState.questionario = payload.questionario;
    navState.ident = payload.ident;
    navState.file = payload.file;

    const dataItem = payload.item || {};
    const respostas = Array.isArray(dataItem.Respostas) ? dataItem.Respostas : [];

    const output = document.getElementById("output");
    const htmlRespostas = respostas
      .map((r) => {
        const opt = (r.opção ?? r.option ?? r.label ?? r.texto ?? "").toString();
        const val = (r.valor ?? r.value ?? "").toString();
        return `<li>${opt || "(sem texto)"}${
          val ? ` <span class="opacity-70">(${val})</span>` : ""
        }</li>`;
      })
      .join("");

    output.innerHTML = `
      <div class="mt-4 p-4 bg-highlight rounded relative">
        <h3 class="text-lg font-bold mb-2 text-accent">Resultado da Análise</h3>

        <div class="flex items-center justify-between gap-2 mb-3">
          <button id="prevBlockBtn"
                  class="px-3 py-1 rounded border border-gray-400 disabled:opacity-40 z-10"
                  data-prev-file="${payload.prev_file ?? ""}"
                  data-prev-ident="${payload.prev_ident ?? ""}"
                  title="Anterior">
            <i class="fas fa-arrow-left"></i>
          </button>

          <div class="text-white text-sm">
            <strong>🧠 Identificador:</strong> ${dataItem.Identificador || "(nenhum)"}<br/>
            <strong>📌 Secção:</strong> ${dataItem["Secção"] || "(Nenhuma)"}<br/>
          </div>

          <button id="nextBlockBtn"
                  class="px-3 py-1 rounded border border-gray-400 disabled:opacity-40 z-10"
                  data-next-file="${payload.next_file ?? ""}"
                  data-next-ident="${payload.next_ident ?? ""}"
                  title="Seguinte">
            <i class="fas fa-arrow-right"></i>
          </button>
        </div>

        <p class="text-white"><strong>❓ Pergunta:</strong> ${dataItem.Pergunta || ""}</p>
        <p class="text-white mt-2"><strong>✅ Respostas:</strong></p>
        <ul class="list-disc pl-6 text-sm text-white">${htmlRespostas}</ul>
      </div>
    `;

    // ligar botões com fallback: usa file se existir, senão ident
    const prevBtn = document.getElementById("prevBlockBtn");
    const nextBtn = document.getElementById("nextBlockBtn");

    if (prevBtn) {
      const prevFile = prevBtn.dataset.prevFile || "";
      const prevIdent = prevBtn.dataset.prevIdent || "";
      prevBtn.disabled = !(prevFile || prevIdent);
      prevBtn.onclick = () => {
        if (prevFile || prevIdent) {
          loadPreviewBlock(navState.questionario, prevIdent || null, prevFile || null);
        }
      };
    }

    if (nextBtn) {
      const nextFile = nextBtn.dataset.nextFile || "";
      const nextIdent = nextBtn.dataset.nextIdent || "";
      nextBtn.disabled = !(nextFile || nextIdent);
      nextBtn.onclick = () => {
        if (nextFile || nextIdent) {
          loadPreviewBlock(navState.questionario, nextIdent || null, nextFile || null);
        }
      };
    }
  }

  // aceita ident OU file (se file presente, usa file)
  function loadPreviewBlock(questionario, ident = null, file = null) {
    let url = `http://localhost:5000/outputs/${encodeURIComponent(questionario)}/item`;
    if (file) {
      url += `?file=${encodeURIComponent(file)}`;
    } else if (ident) {
      url += `?ident=${encodeURIComponent(ident)}`;
    }
    console.log("GET", url);

    fetch(url)
      .then(async (r) => {
        const txt = await r.text();
        if (!r.ok) throw new Error(`${r.status} ${txt}`);
        return JSON.parse(txt);
      })
      .then((payload) => {
        renderPreviewBlock(payload);
        // ✅ garantir que o Continuar usa /finalize também na navegação por blocos
        sessionStorage.setItem("fromPreview", "true");
        sessionStorage.setItem("previewQuestionario", payload.questionario || "");
        attachPreviewActions();
      })
      .catch((err) => {
        console.error("Erro ao carregar bloco:", err);
        showToast("Erro ao carregar bloco do questionário.", "error");
      });
  }

  // atalhos de teclado ← →
  document.addEventListener("keydown", (e) => {
    if (!navState.questionario || !navState.ident) return;
    if (e.key === "ArrowLeft") {
      const prev = document.getElementById("prevBlockBtn");
      if (prev && !prev.disabled) prev.click();
    } else if (e.key === "ArrowRight") {
      const next = document.getElementById("nextBlockBtn");
      if (next && !next.disabled) next.click();
    }
  });

  // ======== UI BASE ========
  function resetUI() {
    sessionStorage.removeItem("pdfLoaded");
    sessionStorage.removeItem("pdfName");
    sessionStorage.removeItem("pdfSize");
    sessionStorage.removeItem("pdfBase64");

    document.getElementById("progressBar").style.width = "0%";
    document.getElementById("output").innerHTML =
      `<p class="text-gray-500 dark:text-gray-400">Nenhum PDF carregado.</p>`;
    document.getElementById("pdfInput").value = "";
    document.getElementById("file-name").textContent = "";

    const oldDownload = document.querySelector("#output a[href$='download-excel']");
    if (oldDownload?.parentElement) {
      oldDownload.parentElement.remove();
    }

    navBusy = false;
    navToken = 0;
    currentPdfFile = null;
    analyzing = false;
    navState = { questionario: null, ident: null };
  }

  function simulatePdfRead(file) {
    const progressBar = document.getElementById("progressBar");
    const output = document.getElementById("output");

    output.innerHTML = `<div class="text-accent animate-pulse text-lg">A processar <strong>${file.name}</strong>...</div>`;
    progressBar.style.width = "0%";
    progressBar.style.transition = "width 1.5s ease-in-out";

    setTimeout(() => (progressBar.style.width = "100%"), 100);
    setTimeout(() => showPdfResult(file), 1800);
  }

  function showPdfResult(file) {
    const output = document.getElementById("output");

    output.innerHTML = `
      <div class="relative bg-white dark:bg-darkCard p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-600 space-y-4">
        <button id="removePdf" class="absolute top-4 right-4 text-white bg-red-500 hover:bg-red-600 rounded-full p-2 shadow-md transition" title="Remover ficheiro">
          <i class="fas fa-times"></i>
        </button>

        <h3 class="text-lg font-semibold text-blue-600 dark:text-blue-400">📄 PDF Carregado</h3>
        <p><strong>Nome:</strong> ${file.name}</p>
        <p><strong>Tamanho:</strong> ${(file.size / 1024).toFixed(2)} KB</p>
        <p><strong>Status:</strong> Pronto para análise</p>

        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <button id="analisarBtn" class="px-5 py-2 border border-accent bg-accent text-white font-semibold rounded-lg shadow-md hover:bg-lightHighlight dark:hover:bg-darkHighlight transition">
            🔍 Analisar PDF
          </button>
        </div>
      </div>
    `;

    document.getElementById("file-name").textContent = "";
    currentPdfFile = file;

    sessionStorage.setItem("pdfLoaded", "true");
    sessionStorage.setItem("pdfName", file.name);
    sessionStorage.setItem("pdfSize", file.size);

    document.getElementById("analisarBtn")?.addEventListener("click", () => {
      if (!analyzing) analisarPdf(currentPdfFile);
    });

    document.getElementById("removePdf")?.addEventListener("click", () => {
      resetUI();
    });

    showToast("PDF carregado com sucesso!", "success");
  }

  function recriarFileDeSession() {
    const base64 = sessionStorage.getItem("pdfBase64");
    const name = sessionStorage.getItem("pdfName");
    const size = parseFloat(sessionStorage.getItem("pdfSize"));

    if (base64 && name && size) {
      const byteCharacters = atob(base64);
      const byteArrays = [];
      for (let offset = 0; offset < byteCharacters.length; offset += 512) {
        const slice = byteCharacters.slice(offset, offset + 512);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
          byteNumbers[i] = slice.charCodeAt(i);
        }
        byteArrays.push(new Uint8Array(byteNumbers));
      }

      const blob = new Blob(byteArrays, { type: "application/pdf" });
      return new File([blob], name, { type: "application/pdf" });
    }

    return null;
  }

  // ======== BOTÕES CONTINUAR / NÃO GOSTO (RE-ANEXO DINÂMICO) ========
  function attachPreviewActions() {
    const output = document.getElementById("output");

    // remover instâncias antigas (inclui o wrapper, para não acumular)
    output.querySelectorAll(".continuar-btn, .naogosto-btn, .actions-wrap").forEach((el) => el.remove());

    // wrapper para os botões
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "actions-wrap mt-4 flex flex-wrap items-center gap-2";

    // continuar
    const continuarBtn = document.createElement("button");
    continuarBtn.textContent = "✅ Continuar com processamento automático";
    continuarBtn.className =
      "px-4 py-2 bg-green-600 text-white rounded-lg shadow hover:bg-green-700 transition continuar-btn";

    // não gosto
    const naoGostoBtn = document.createElement("button");
    naoGostoBtn.textContent = "❌ Não gosto da resposta";
    naoGostoBtn.className =
      "px-4 py-2 bg-red-600 text-white rounded-lg shadow hover:bg-red-700 transition naogosto-btn";

    actionsWrap.appendChild(continuarBtn);
    actionsWrap.appendChild(naoGostoBtn);
    output.appendChild(actionsWrap);

    // handler CONTINUAR
    continuarBtn.addEventListener("click", async () => {
      const fromPreview = sessionStorage.getItem("fromPreview") === "true";
      const questionario = sessionStorage.getItem("previewQuestionario") || navState.questionario;

      if (!fromPreview || !questionario) {
        showToast("Sem contexto de preview — a continuar pelo modo automático…", "warning");
        // cai no fluxo antigo
        const base64 = sessionStorage.getItem("pdfBase64");
        const name = sessionStorage.getItem("pdfName");
        const size = parseFloat(sessionStorage.getItem("pdfSize"));
        if (base64 && name && size) {
          const byteCharacters = atob(base64);
          const byteArrays = [];
          for (let offset = 0; offset < byteCharacters.length; offset += 512) {
            const slice = byteCharacters.slice(offset, offset + 512);
            const byteNumbers = new Array(slice.length);
            for (let i = 0; i < slice.length; i++) byteNumbers[i] = slice.charCodeAt(i);
            byteArrays.push(new Uint8Array(byteNumbers));
          }
          const blob = new Blob(byteArrays, { type: "application/pdf" });
          const file = new File([blob], name, { type: "application/pdf" });
          analisarPdf(file, "automatico");
        } else {
          showToast("Erro: ficheiro PDF não encontrado.", "error");
        }
        return;
      }

      // estado de carregamento (sem remover os botões!)
      continuarBtn.disabled = true;
      naoGostoBtn.disabled = true;
      const prevText = continuarBtn.textContent;
      continuarBtn.textContent = "A finalizar...";

      try {
        const resp = await fetch(
          `http://localhost:5000/outputs/${encodeURIComponent(questionario)}/finalize`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ strategy: "use_preview_blocks" }),
          }
        );
        const data = await resp.json().catch(() => ({}));
        console.log("Finalize response:", data);
        if (!resp.ok || data.ok === false) {
          throw new Error(data.mensagem || `HTTP ${resp.status}`);
        }

        // substitui o conteúdo pelo resultado
        const out = document.getElementById("output");
        out.innerHTML = `
          <div class="mt-4 p-4 bg-highlight rounded">
            <h3 class="text-lg font-bold mb-2 text-accent">Resultado da Consolidação</h3>
            <p class="text-sm text-white">${data.mensagem || "Blocos consolidados a partir do preview."}</p>
          </div>
        `;

        // mostrar botão de download se houver excel
        const excelReady = data.excel === true || !!data.download_excel;
        if (excelReady) {
          const downloadContainer = document.createElement("div");
          downloadContainer.className = "mt-4 flex justify-center";
          const downloadBtn = document.createElement("a");
          downloadBtn.href = data.download_excel || "http://localhost:5000/download-excel";
          downloadBtn.download = true;
          downloadBtn.className =
            "inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg shadow-md transition";
          downloadBtn.textContent = "⬇️ Descarregar Excel Gerado";
          downloadContainer.appendChild(downloadBtn);
          out.appendChild(downloadContainer);
        }

        // limpar flags para não refazer finalize sem querer
        sessionStorage.removeItem("fromPreview");
        sessionStorage.removeItem("previewQuestionario");

        showToast("Consolidação concluída com sucesso!", "success");
      } catch (err) {
        console.error(err);
        showToast("Erro ao consolidar a partir do preview.", "error");
        // reativar botões e texto
        continuarBtn.disabled = false;
        naoGostoBtn.disabled = false;
        continuarBtn.textContent = prevText;
      }
    });

    // handler NÃO GOSTO (modal)
    const ensureModal = () => {
      if (document.getElementById("feedbackModal")) return;

      const modal = document.createElement("div");
      modal.id = "feedbackModal";
      modal.className =
        "fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 hidden backdrop-blur-sm";
      modal.innerHTML = `
        <div class="bg-white dark:bg-darkCard rounded-xl p-6 w-full max-w-xl shadow-lg relative">
          <button id="closeModalBtn" class="absolute top-3 right-3 text-gray-500 hover:text-red-600">
            <i class="fas fa-times text-xl"></i>
          </button>
          <h3 class="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">Adicionar instruções personalizadas para o LLM</h3>
          <textarea id="modalTextarea" rows="6" class="w-full p-3 border border-gray-300 rounded dark:bg-darkHighlight dark:text-white"></textarea>
          <button id="saveSuggestionBtn" class="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">💾 Usar estas instruções</button>
        </div>
      `;
      document.body.appendChild(modal);

      modal.querySelector("#closeModalBtn").addEventListener("click", () => modal.classList.add("hidden"));
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
      });

      modal.querySelector("#saveSuggestionBtn").addEventListener("click", () => {
        const texto = modal.querySelector("#modalTextarea").value.trim();
        if (!texto) return showToast("Por favor escreva algo primeiro.", "warning");

        const questionario = navState.questionario;
        const ident = navState.ident || "";
        const file = navState.file || "";
        if (!questionario || (!ident && !file)) return showToast("Bloco atual não identificado.", "error");

        const btn = modal.querySelector("#saveSuggestionBtn");
        btn.disabled = true;
        btn.textContent = "A reprocessar bloco...";

        fetch(`http://localhost:5000/outputs/${encodeURIComponent(questionario)}/item/reprocess`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ident, file, instructions: texto }),
        })
          .then(async (r) => {
            const txt = await r.text();
            if (!r.ok) throw new Error(`${r.status} ${txt}`);
            return JSON.parse(txt);
          })
          .then((payload) => {
            modal.classList.add("hidden");
            showToast("Bloco reprocessado com as instruções dadas.", "success");
            renderPreviewBlock(payload);
            attachPreviewActions();
          })
          .catch((err) => {
            console.error(err);
            showToast("Erro ao reprocessar o bloco.", "error");
          })
          .finally(() => {
            btn.disabled = false;
            btn.textContent = "💾 Usar estas instruções";
          });
      });
    };

    ensureModal();
    naoGostoBtn.addEventListener("click", () => {
      const modal = document.getElementById("feedbackModal");
      if (modal) {
        modal.classList.remove("hidden");
        modal.querySelector("#modalTextarea").value = "";
      }
    });
  }

  // ======== PROCESSAMENTO ========
  function analisarPdf(file, modoForcado = null) {
    analyzing = true;
    navState = { questionario: null, ident: null };
    navBusy = false;
    navToken = 0;
    const output = document.getElementById("output");
    const button = document.getElementById("analisarBtn");

    if (!file || !button) return;

    button.disabled = true;
    button.textContent = "Analisando...";

    const loader = document.createElement("div");
    loader.className = "mt-6 text-accent flex items-center gap-2";
    loader.innerHTML = `
      <svg class="animate-spin h-5 w-5 text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4"></path>
      </svg> A analisar o PDF...`;
    output.appendChild(loader);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("modo", modoForcado || modoAtual);

    const instrucaoExtra = sessionStorage.getItem("instrucoesPersonalizadas");
    if (instrucaoExtra) {
      formData.append("instrucoes", instrucaoExtra);
      sessionStorage.removeItem("instrucoesPersonalizadas");
    }

    fetch("http://localhost:5000/upload", {
      method: "POST",
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        loader.remove();

        // limpa previews e botões antigos
        document.querySelectorAll(".continuar-btn, .naogosto-btn, .actions-wrap").forEach((el) => el.remove());

        if (modoAtual === "preview") {
          // Novo formato (recomendado): {questionario, ident, prev_ident, next_ident, item, file}
          if (data && data.item && data.ident && data.questionario) {
            renderPreviewBlock(data);
            // ✅ marca fromPreview logo no 1º payload do /upload
            sessionStorage.setItem("fromPreview", "true");
            sessionStorage.setItem("previewQuestionario", data.questionario || "");
            attachPreviewActions();
          }
          // Compat: formato antigo flat {Pergunta, ...}
          else if (data && data.Pergunta) {
            const questionarioSlug = (sessionStorage.getItem("pdfName") || "Questionario")
              .replace(/\.[Pp][Dd][Ff]$/, "")
              .replace(/[^A-Za-z0-9._-]+/g, "_");
            renderPreviewBlock({
              questionario: questionarioSlug,
              ident: data.Identificador || "SEM.ID",
              prev_ident: null,
              next_ident: null,
              item: data,
              file: null,
            });
            // ✅ marca fromPreview aqui também (compat)
            sessionStorage.setItem("fromPreview", "true");
            sessionStorage.setItem("previewQuestionario", questionarioSlug);
            attachPreviewActions();
          } else {
            showToast("Preview inválido: resposta inesperada da API.", "error");
          }
        } else {
          // automático (tal como tinhas)
          const resultadoDiv = document.createElement("div");
          resultadoDiv.className = "mt-4 p-4 bg-highlight rounded";
          resultadoDiv.innerHTML = `<h3 class="text-lg font-bold mb-2 text-accent">Resultado da Análise</h3>`;
          resultadoDiv.innerHTML += `<p class="text-sm text-white">${
            data.mensagem || "Análise concluída."
          }</p>`;
          output.innerHTML = "";
          output.appendChild(resultadoDiv);

          const downloadContainer = document.createElement("div");
          downloadContainer.className = "mt-4 flex justify-center";

          const downloadBtn = document.createElement("a");
          downloadBtn.href = "http://localhost:5000/download-excel";
          downloadBtn.download = true;
          downloadBtn.className =
            "inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg shadow-md transition";
          downloadBtn.textContent = "⬇️ Descarregar Excel Gerado";

          downloadContainer.appendChild(downloadBtn);
          output.appendChild(downloadContainer);
        }

        showToast("Análise concluída com sucesso!", "success");

        // histórico (mantido)
        const user = JSON.parse(localStorage.getItem("user"));
        const novoFile = recriarFileDeSession();
        if (modoAtual === "automatico") {
          if (user && user.email && novoFile) {
            const historicoData = new FormData();
            historicoData.append("pdf", novoFile);
            historicoData.append("email", user.email);

            fetch("http://localhost:5000/api/user/upload_pdf", {
              method: "POST",
              body: historicoData,
            })
              .then((res) => res.json())
              .then((histData) => {
                if (histData.status?.toLowerCase().includes("sucesso")) {
                  console.log("Histórico guardado com sucesso!");
                } else {
                  console.warn("Falha ao guardar histórico:", histData);
                }
              })
              .catch((err) => {
                console.error("Erro ao guardar histórico do PDF:", err);
              });
          }
        }
      })
      .catch((err) => {
        loader.remove();
        showToast("Erro ao analisar o PDF.", "error");
        console.error(err);
      })
      .finally(() => {
        const button = document.getElementById("analisarBtn");
        if (button) {
          button.disabled = false;
          button.textContent = "Analisar PDF";
        }
        analyzing = false;
      });
  }

  function handleFile(file) {
    if (!file || file.type !== "application/pdf") {
      showToast("Por favor selecione um ficheiro PDF válido.", "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
      const base64 = e.target.result.split(",")[1];
      sessionStorage.setItem("pdfBase64", base64);
      sessionStorage.setItem("pdfName", file.name);
      sessionStorage.setItem("pdfSize", file.size);
      sessionStorage.setItem("pdfLoaded", "true");
      simulatePdfRead(file);
    };
    reader.readAsDataURL(file);
  }

  function setupPdfUpload() {
    const input = document.getElementById("pdfInput");
    const dropzone = document.getElementById("dropzone");

    input.addEventListener("change", () => {
      if (input.files.length) handleFile(input.files[0]);
    });

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("bg-lightHighlight", "dark:bg-darkHighlight");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("bg-lightHighlight", "dark:bg-darkHighlight");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("bg-lightHighlight", "dark:bg-darkHighlight");
      if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    dropzone.addEventListener("click", () => input.click());
  }

  setupPdfUpload();
  resetUI();

  if (sessionStorage.getItem("pdfLoaded") === "true") {
    const base64 = sessionStorage.getItem("pdfBase64");
    const name = sessionStorage.getItem("pdfName");
    const size = parseFloat(sessionStorage.getItem("pdfSize"));

    if (base64 && name && size) {
      const byteCharacters = atob(base64);
      const byteArrays = [];
      for (let offset = 0; offset < byteCharacters.length; offset += 512) {
        const slice = byteCharacters.slice(offset, offset + 512);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
          byteNumbers[i] = slice.charCodeAt(i);
        }
        byteArrays.push(new Uint8Array(byteNumbers));
      }

      const blob = new Blob(byteArrays, { type: "application/pdf" });
      const file = new File([blob], name, { type: "application/pdf" });
      currentPdfFile = file;
      showPdfResult(file);
    }
  }

  const modoToggle = document.getElementById("modoToggle");
  const modoText = document.getElementById("modoText");

  if (modoToggle && modoText) {
    modoToggle.checked = modoAtual === "automatico";
    modoText.textContent = `Modo ${modoAtual.charAt(0).toUpperCase() + modoAtual.slice(1)}`;

    modoToggle.addEventListener("change", () => {
      modoAtual = modoToggle.checked ? "automatico" : "preview";
      modoText.textContent = `Modo ${modoAtual.charAt(0).toUpperCase() + modoAtual.slice(1)}`;
      localStorage.setItem("modo", modoAtual);
    });
  }
}

window.loadIngest = loadIngest;
