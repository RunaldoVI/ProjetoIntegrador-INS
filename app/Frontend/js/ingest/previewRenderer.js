// Frontend/js/ingest/previewRenderer.js
window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  // herdar cor principal se existir (para focus)
  function syncBrandFromSite() {
    const ref = document.querySelector('.btn-primary, .button-primary, .btn.btn-primary, .btn-brand, .primary, .uk-button-primary, a.btn[href], .action-primary, button[type="submit"]');
    if (!ref) return;
    const cs = getComputedStyle(ref);
    const src = cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)' ? cs.backgroundColor : cs.color;
    const m = (src.match(/\d+/g)||[]).map(n=>parseInt(n,10));
    if (m.length >= 3) {
      const root = document.documentElement.style;
      root.setProperty('--brand-r', m[0]);
      root.setProperty('--brand-g', m[1]);
      root.setProperty('--brand-b', m[2]);
    }
  }

  ns.previewRenderer = {
    render(payload, loadPreviewBlock) {
      syncBrandFromSite();

      if (typeof ns.setNav === "function") {
        ns.setNav(payload.questionario, payload.ident, payload.file);
      }

      const item = payload.item || {};
      const answers = Array.isArray(item.Respostas) ? item.Respostas : [];

      const output = document.getElementById("output");
      output.innerHTML = `
        <div class="pv5-wrap">

          <section class="pv5-group">
            <div class="pv5-row">
              <span class="pv5-label"><span class="pv5-ico">🧠</span> Identificador:</span>
              <div class="pv5-value">${item.Identificador || "—"}</div>
            </div>

            <hr class="pv5-divider">

            <div class="pv5-row">
              <span class="pv5-label"><span class="pv5-ico">📌</span> Secção:</span>
              <div class="pv5-value">${item["Secção"] || "—"}</div>
            </div>

            <hr class="pv5-divider">

            <div class="pv5-row">
              <span class="pv5-label"><span class="pv5-ico">❓</span> Pergunta:</span>
              <div class="pv5-value">${item.Pergunta || ""}</div>
            </div>
          </section>

          <section class="pv5-group">
            <h3 class="pv5-title">Respostas</h3>
            <ul class="pv5-list" role="list">
              ${answers.map((ans, i) => {
                const label = (ans.opção ?? ans.option ?? ans.label ?? ans.texto ?? "").toString() || "(sem texto)";
                const valueStr = (ans.valor ?? ans.value ?? "")?.toString?.() ?? "";
                return `
                  <li class="pv5-item" tabindex="0" ${i%2? 'style="border-left:1px solid var(--sep)"':''}>
                    <span class="pv5-dot"></span>
                    <span style="color:#fff">${label}</span>
                    ${valueStr ? `<span class="pv5-count">${valueStr}</span>` : ""}
                  </li>`;
              }).join("")}
            </ul>
          </section>

          <div class="pv5-pager">
            <button id="prevBlockBtn" class="pv5-btn" title="Anterior"
              data-prev-file="${payload.prev_file ?? ""}" data-prev-ident="${payload.prev_ident ?? ""}">
              <i class="fas fa-arrow-left" aria-hidden="true"></i>
            </button>
            <button id="nextBlockBtn" class="pv5-btn" title="Seguinte"
              data-next-file="${payload.next_file ?? ""}" data-next-ident="${payload.next_ident ?? ""}">
              <i class="fas fa-arrow-right" aria-hidden="true"></i>
            </button>
          </div>
        </div>
      `;

      // Navegação
      const prevBtn = document.getElementById("prevBlockBtn");
      const nextBtn = document.getElementById("nextBlockBtn");

      if (prevBtn) {
        const prevFile = prevBtn.dataset.prevFile || "";
        const prevIdent = prevBtn.dataset.prevIdent || "";
        prevBtn.disabled = !(prevFile || prevIdent);
        prevBtn.onclick = () => {
          if ((prevFile || prevIdent) && typeof loadPreviewBlock === "function") {
            loadPreviewBlock(payload.questionario, prevIdent || null, prevFile || null);
          }
        };
      }
      if (nextBtn) {
        const nextFile = nextBtn.dataset.nextFile || "";
        const nextIdent = nextBtn.dataset.nextIdent || "";
        nextBtn.disabled = !(nextFile || nextIdent);
        nextBtn.onclick = () => {
          if ((nextFile || nextIdent) && typeof loadPreviewBlock === "function") {
            loadPreviewBlock(payload.questionario, nextIdent || null, nextFile || null);
          }
        };
      }
    }
  };
})(window.IngestHelpers);
