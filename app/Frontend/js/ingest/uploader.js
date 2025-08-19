window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  const { state, session, ui, flow } = ns;

  function handlePdfFile(file) {
    if (!file || file.type !== "application/pdf") {
      showToast("Por favor selecione um ficheiro PDF válido.", "error");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target.result.split(",")[1];
      session.set("pdfBase64", base64);
      session.set("pdfName", file.name);
      session.set("pdfSize", file.size);
      session.set("pdfLoaded", "true");

      const progressBar = document.getElementById("progressBar");
      const output = document.getElementById("output");
      output.innerHTML = `<div class="text-accent animate-pulse text-lg">A processar <strong>${file.name}</strong>...</div>`;
      progressBar.style.width = "0%";
      progressBar.style.transition = "width 1.5s ease-in-out";
      setTimeout(() => (progressBar.style.width = "100%"), 100);
      setTimeout(() => {
        state.currentPdfFile = file;
        ui.renderLoadedPdfCard(
          file,
          () => { if (!state.isAnalyzing) flow.analyzePdf(file); },
          ui.resetUI
        );
        showToast("PDF carregado com sucesso!", "success");
      }, 1800);
    };
    reader.readAsDataURL(file);
  }

  function setupPdfUpload() {
    const input = document.getElementById("pdfInput");
    const dropzone = document.getElementById("dropzone");
    input?.addEventListener("change", () => { if (input.files.length) handlePdfFile(input.files[0]); });
    dropzone?.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("bg-lightHighlight", "dark:bg-darkHighlight"); });
    dropzone?.addEventListener("dragleave", () => { dropzone.classList.remove("bg-lightHighlight", "dark:bg-darkHighlight"); });
    dropzone?.addEventListener("drop", (e) => { e.preventDefault(); dropzone.classList.remove("bg-lightHighlight", "dark:bg-darkHighlight"); if (e.dataTransfer.files.length) handlePdfFile(e.dataTransfer.files[0]); });
    dropzone?.addEventListener("click", () => {input.value = ""; input.click(); });
  }

  ns.uploader = { setupPdfUpload, handlePdfFile };
})(window.IngestHelpers);
