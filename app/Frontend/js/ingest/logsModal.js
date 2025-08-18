window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  ns.logsModal = {
    async open() {
      try {
        const data = await ns.apiClient.getLogs(800);
        const lines = Array.isArray(data.lines) ? data.lines : [];
        const modal = document.createElement("div");
        modal.className = "fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4";
        modal.innerHTML = `
          <div class="bg-[#1b1e2a] max-w-4xl w-full rounded-xl overflow-hidden shadow-xl">
            <div class="flex items-center justify-between px-4 py-3 border-b border-white/10">
              <h4 class="text-white font-semibold">Logs de processamento</h4>
              <button id="closeLogs" class="text-white/70 hover:text-white">✕</button>
            </div>
            <pre class="p-4 max-h-[70vh] overflow-auto text-sm text-white/80 whitespace-pre-wrap">${
              lines.join("\n") || "Sem logs."
            }</pre>
          </div>`;
        document.body.appendChild(modal);
        modal.querySelector("#closeLogs").onclick = () => modal.remove();
        modal.addEventListener("click", (e) => { if (e.target === modal) modal.remove(); });
      } catch {
        showToast("Não foi possível carregar os logs.", "error");
      }
    }
  };
})(window.IngestHelpers);
