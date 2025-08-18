window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  ns.previewActions = {
    mount(onContinue, onDislike) {
      const container = document.getElementById("actionsMount") || document.getElementById("output");
      container.querySelector(".actions-wrap")?.remove();

      const wrap = document.createElement("div");
      wrap.className = "actions-wrap mt-4 flex flex-wrap items-center gap-2";

      const continueBtn = document.createElement("button");
      continueBtn.className = "continuar-btn px-4 py-2 bg-green-600 text-white rounded-lg shadow hover:bg-green-700 transition";
      continueBtn.textContent = "✅ Continuar com processamento automático";

      const dislikeBtn = document.createElement("button");
      dislikeBtn.className = "naogosto-btn px-4 py-2 bg-red-600 text-white rounded-lg shadow hover:bg-red-700 transition";
      dislikeBtn.textContent = "❌ Não gosto da resposta";

      wrap.appendChild(continueBtn);
      wrap.appendChild(dislikeBtn);
      container.appendChild(wrap);

      // ligar callbacks fornecidos pelo ingest.js
      continueBtn.addEventListener("click", onContinue);
      dislikeBtn.addEventListener("click", onDislike);
    }
  };
})(window.IngestHelpers);
