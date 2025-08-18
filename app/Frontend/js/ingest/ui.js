window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  const { state, session } = ns;

  function resetUI() {
    session.del("pdfLoaded"); session.del("pdfName"); session.del("pdfSize"); session.del("pdfBase64");
    document.getElementById("progressBar").style.width = "0%";
    document.getElementById("output").innerHTML = `<p class="text-gray-500 dark:text-gray-400">Nenhum PDF carregado.</p>`;
    document.getElementById("pdfInput").value = "";
    document.getElementById("file-name").textContent = "";
    state.nav = { questionnaire: null, ident: null, file: null };
    state.currentPdfFile = null;
    state.isAnalyzing = false;
  }

  function recreateFileFromSession() {
    const base64 = session.get("pdfBase64");
    const name = session.get("pdfName");
    const size = parseFloat(session.get("pdfSize"));
    if (!base64 || !name || !size) return null;

    const bytes = atob(base64);
    const chunks = [];
    for (let i = 0; i < bytes.length; i += 512) {
      const slice = bytes.slice(i, i + 512);
      const arr = new Array(slice.length);
      for (let j = 0; j < slice.length; j++) arr[j] = slice.charCodeAt(j);
      chunks.push(new Uint8Array(arr));
    }
    return new File([new Blob(chunks, { type: "application/pdf" })], name, { type: "application/pdf" });
  }

  function renderLoadedPdfCard(file, onAnalyze, onRemove) {
    const out = document.getElementById("output");
    out.innerHTML = `
      <div class="relative bg-white dark:bg-darkCard p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-600 space-y-4">
        <button id="removePdf" class="absolute top-4 right-4 text-white bg-red-500 hover:bg-red-600 rounded-full p-2 shadow-md transition" title="Remover ficheiro"><i class="fas fa-times"></i></button>
        <h3 class="text-lg font-semibold text-blue-600 dark:text-blue-400">📄 PDF Carregado</h3>
        <p><strong>Nome:</strong> ${file.name}</p>
        <p><strong>Tamanho:</strong> ${(file.size / 1024).toFixed(2)} KB</p>
        <p><strong>Status:</strong> Pronto para análise</p>
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <button id="analisarBtn" class="px-5 py-2 border border-accent bg-accent text-white font-semibold rounded-lg shadow-md hover:bg-lightHighlight dark:hover:bg-darkHighlight transition">🔍 Analisar PDF</button>
        </div>
      </div>`;
    document.getElementById("analisarBtn")?.addEventListener("click", onAnalyze);
    document.getElementById("removePdf")?.addEventListener("click", onRemove);
  }

  ns.ui = { resetUI, recreateFileFromSession, renderLoadedPdfCard };
})(window.IngestHelpers);
