function loadIngest() {
  console.log("ingest.js carregado com sucesso!");

  let modoAtual = "automatico";
  let currentPdfFile = null;
  let analyzing = false;

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

    // Remover botão de download se existir
    const oldDownload = document.querySelector("#output a[href$='download-excel']");
    if (oldDownload?.parentElement) {
      oldDownload.parentElement.remove();
    }

    currentPdfFile = null;
    analyzing = false;
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

  function analisarPdf(file) {
    analyzing = true;
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
    formData.append("modo", modoAtual);

    fetch("http://localhost:5000/upload", {
      method: "POST",
      body: formData,
    })
      .then(res => res.json())
.then(data => {
  loader.remove();

  const resultadoDiv = document.createElement("div");
  resultadoDiv.className = "mt-4 p-4 bg-highlight rounded";
  resultadoDiv.innerHTML = `<h3 class="text-lg font-bold mb-2 text-accent">Resultado da Análise</h3>`;

  if (modoAtual === "preview" && data.Pergunta) {
    resultadoDiv.innerHTML += `
      <p class="text-white"><strong>🧠 Identificador:</strong> ${data.Identificador || "(nenhum)"}</p>
      <p class="text-white"><strong>📌 Secção:</strong> ${data.Secção || "(Nenhuma)"}</p>
      <p class="text-white"><strong>❓ Pergunta:</strong> ${data.Pergunta}</p>
      <p class="text-white"><strong>✅ Respostas:</strong></p>
      <ul class="list-disc pl-6 text-sm text-white">
        ${(data.Respostas || []).map(r => `<li>${r}</li>`).join("")}
      </ul>
    `;

    output.appendChild(resultadoDiv);

    const continuarBtn = document.createElement("button");
    continuarBtn.textContent = "✅ Continuar com processamento automático";
    continuarBtn.className = "mt-6 px-4 py-2 bg-green-600 text-white rounded-lg shadow hover:bg-green-700 transition";
    continuarBtn.addEventListener("click", () => {
      continuarBtn.disabled = true;
      continuarBtn.textContent = "A continuar...";
      modoAtual = "automatico";
      document.getElementById("modoToggle").textContent = "🔄 Modo: Automático";
      analisarPdf(currentPdfFile);
    });

    output.appendChild(continuarBtn);

  } else {
    resultadoDiv.innerHTML += `<p class="text-sm text-white">${data.mensagem || "Análise concluída."}</p>`;
    output.appendChild(resultadoDiv);

    const downloadContainer = document.createElement("div");
    downloadContainer.className = "mt-4 flex justify-center";

    const downloadBtn = document.createElement("a");
    downloadBtn.href = "http://localhost:5000/download-excel";
    downloadBtn.download = true;
    downloadBtn.className = "inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg shadow-md transition";
    downloadBtn.textContent = "⬇️ Descarregar Excel Gerado";

    downloadContainer.appendChild(downloadBtn);
    output.appendChild(downloadContainer);
  }

  showToast("Análise concluída com sucesso!", "success");
})
      .catch(err => {
        loader.remove();
        showToast("Erro ao analisar o PDF.", "error");
        console.error(err);
      })
      .finally(() => {
        button.disabled = false;
        button.textContent = "Analisar PDF";
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
      const base64 = e.target.result.split(',')[1];
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

    dropzone.addEventListener("dragover", e => {
      e.preventDefault();
      dropzone.classList.add("bg-lightHighlight", "dark:bg-darkHighlight");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("bg-lightHighlight", "dark:bg-darkHighlight");
    });

    dropzone.addEventListener("drop", e => {
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



  document.getElementById("modoToggle")?.addEventListener("click", () => {
  modoAtual = (modoAtual === "automatico") ? "preview" : "automatico";
  document.getElementById("modoToggle").textContent = `🔄 Modo: ${modoAtual.charAt(0).toUpperCase() + modoAtual.slice(1)}`;
});


}

window.loadIngest = loadIngest;
