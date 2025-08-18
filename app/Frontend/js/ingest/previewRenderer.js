// Frontend/js/ingest/previewRenderer.js
window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  function ensurePreviewStyles() {
    if (document.getElementById("preview-style-v8-flatlabels")) return;
    const css = `
    :root{
      --sep: rgba(255,255,255,.08);
      --hover: rgba(255,255,255,.06);
      --pill-weak: rgba(255,255,255,.06);
      --text-muted: rgba(255,255,255,.75);
      --brand-r: 59; --brand-g: 130; --brand-b: 246;
    }

    /* ===== layout minimal ===== */
    .pv5-wrap{display:flex;flex-direction:column;gap:18px}

    /* grupo sem caixas; só separadores */
    .pv5-group{display:flex;flex-direction:column;gap:12px}
    .pv5-divider{height:1px;background:var(--sep);border:0}

    /* linha label + valor – rótulo sem bolha (fundo/contorno removidos) */
    .pv5-row{display:flex;align-items:center;gap:10px}
    .pv5-label{
      display:inline-flex;align-items:center;gap:.45rem;
      padding:0; border:0; border-radius:0; background:transparent;
      color:#fff; font-weight:700; white-space:nowrap;
    }
    .pv5-label .pv5-ico{opacity:.9}
    .pv5-value{color:#fff;opacity:.95;flex:1}

    /* título */
    .pv5-title{color:#fff;font-weight:700;margin:0}

    /* respostas */
    .pv5-list{
      display:grid;grid-template-columns:1fr;gap:0;
      border:1px solid var(--sep);border-radius:12px;overflow:hidden
    }
    @media(min-width:900px){.pv5-list{grid-template-columns:1fr 1fr}}
    .pv5-item{
      display:flex;align-items:center;gap:.7rem;padding:.85rem 1rem;
      border-bottom:1px solid var(--sep);background:transparent;
      transition:background .12s ease
    }
    .pv5-item:nth-child(2n){border-left:1px solid var(--sep)}
    .pv5-item:hover{background:var(--hover)}
    .pv5-dot{width:7px;height:7px;border-radius:999px;background:var(--text-muted)}
    .pv5-count{
      margin-left:auto;font-size:.78rem;color:#fff;
      padding:.15rem .45rem;border-radius:999px;
      background:var(--pill-weak);border:1px solid var(--sep)
    }
    .pv5-item:focus-within{outline:2px solid rgba(var(--brand-r),var(--brand-g),var(--brand-b),.35);outline-offset:2px}

    /* pager */
    .pv5-pager{display:flex;justify-content:flex-end;gap:.5rem}
    .pv5-btn{
      display:inline-flex;align-items:center;justify-content:center;
      width:38px;height:38px;border-radius:10px;border:1px solid var(--sep);
      background:var(--pill-weak);color:#fff;transition:background .15s
    }
    .pv5-btn:hover{background:rgba(var(--brand-r),var(--brand-g),var(--brand-b),.12)}
    `;
    const style = document.createElement("style");
    style.id = "preview-style-v8-flatlabels";
    style.textContent = css;
    document.head.appendChild(style);
  }

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
      ensurePreviewStyles();
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
