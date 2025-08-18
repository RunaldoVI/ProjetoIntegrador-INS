function loadIngest() {
  console.log("ingest.js (modular) carregado com sucesso!");

  const { state, session, setProcessingMode, logsModal, ui, uploader, flow } = window.IngestHelpers;

  // atalhos ← →
  document.addEventListener("keydown", (e) => {
    const { questionnaire, ident } = state.nav || {};
    if (!questionnaire || !ident) return;
    if (e.key === "ArrowLeft") document.getElementById("prevBlockBtn")?.click();
    else if (e.key === "ArrowRight") document.getElementById("nextBlockBtn")?.click();
  });

  // botão global de logs (se existir)
  document.getElementById("verLogsBtn")?.addEventListener("click", logsModal.open);

  // init
  uploader.setupPdfUpload();
  ui.resetUI();

  if (session.get("pdfLoaded") === "true") {
    const file = ui.recreateFileFromSession();
    if (file) {
      state.currentPdfFile = file;
      ui.renderLoadedPdfCard(file, () => { if (!state.isAnalyzing) flow.analyzePdf(file); }, ui.resetUI);
    }
  }

  // toggle modo
  const modeToggle = document.getElementById("modoToggle");
  const modeText = document.getElementById("modoText");
  if (modeToggle && modeText) {
    modeToggle.checked = state.processingMode === "automatico";
    modeText.textContent = `Modo ${state.processingMode[0].toUpperCase() + state.processingMode.slice(1)}`;
    modeToggle.addEventListener("change", () => {
      setProcessingMode(modeToggle.checked ? "automatico" : "preview");
      modeText.textContent = `Modo ${state.processingMode[0].toUpperCase() + state.processingMode.slice(1)}`;
    });
  }
}
window.loadIngest = loadIngest;
