export const ChatbotBubble = (() => {
  const CONFIG = {
    apiUrl: "http://localhost:5000/chat-rag",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    simulateStreaming: true,
  };

  Object.defineProperty(CONFIG, "apiUrl", {
    value: CONFIG.apiUrl,
    writable: false,
    configurable: false,
    enumerable: true
  });

  const API_URL = CONFIG.apiUrl;
  const qs = (sel, root = document) => root.querySelector(sel);
  const els = {};

  function markup() {
    return `
  <button class="cb-launcher" id="cbLauncher" aria-label="Abrir chatbot">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M21 15a4 4 0 0 1-4 4H7l-4 4V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/>
    </svg>
    <span class="cb-badge" id="cbBadge">1</span>
  </button>

  <section class="cb-panel" id="cbPanel" role="dialog" aria-label="Chatbot" aria-modal="false">
    <header class="cb-header" id="cbHeader">
      <div class="cb-avatar" aria-hidden="true">AI</div>
      <div>
        <div class="cb-title">Assistente</div>
        <div class="cb-subtitle">Online agora</div>
      </div>
      <div class="cb-spacer"></div>
      <button class="cb-btn" id="cbClose" title="Fechar" aria-label="Fechar">
        <svg class="cb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </header>

    <main class="cb-body" id="cbBody" tabindex="0" aria-live="polite">
      <div class="cb-message">
        <div class="cb-bubble">Olá! 👋
Sou o teu assistente. Faz-me perguntas sobre o site ou o teu projeto quando quiseres.</div>
      </div>
    </main>

    <footer class="cb-footer">
      <div class="cb-suggestions" id="cbSuggestions">
        <span class="cb-chip" data-q="O que posso fazer aqui?">O que posso fazer aqui?</span>
        <span class="cb-chip" data-q="Como mudar para modo escuro?">Como mudar para modo escuro?</span>
        <span class="cb-chip" data-q="Onde vejo os PDFs ingeridos?">Onde vejo os PDFs ingeridos?</span>
      </div>
      <div class="cb-input-wrap">
        <svg class="cb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M21.44 11.05 4.12 3.2a1 1 0 0 0-1.36 1.28l3.06 7.16a1 1 0 0 1 0 .73l-3.06 7.16a1 1 0 0 0 1.36 1.28l17.32-7.85a1 1 0 0 0 0-1.91Z"/></svg>
        <input id="cbInput" class="cb-input" type="text" placeholder="Escreve aqui e carrega Enter…" aria-label="Mensagem para o assistente" />
        <button id="cbSend" class="cb-send" title="Enviar" aria-label="Enviar">
          <svg class="cb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </button>
      </div>
    </footer>
  </section>`;
  }

  function addMessage(content, who = "bot") {
    const wrap = document.createElement("div");
    wrap.className = `cb-message ${who === "you" ? "you" : ""}`;
    const bubble = document.createElement("div");
    bubble.className = "cb-bubble";
    bubble.textContent = content;
    const time = document.createElement("div");
    time.className = "cb-time";
    time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    wrap.appendChild(bubble);
    wrap.appendChild(time);
    els.body.appendChild(wrap);
    els.body.scrollTop = els.body.scrollHeight;
  }

  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "cb-message";
    wrap.id = "cbTyping";
    const bubble = document.createElement("div");
    bubble.className = "cb-bubble";
    bubble.innerHTML = '<span class="cb-typing" aria-label="A escrever"><span></span><span></span><span></span></span>';
    wrap.appendChild(bubble);
    els.body.appendChild(wrap);
    els.body.scrollTop = els.body.scrollHeight;
  }

  function removeTyping() {
    const t = qs("#cbTyping");
    if (t) t.remove();
  }

  function togglePanel(show) {
    const visible = show ?? (els.panel.style.display === "none" || els.panel.style.display === "");
    els.panel.style.display = visible ? "flex" : "none";
    if (visible) {
      els.body.scrollTop = els.body.scrollHeight;
      els.badge.style.display = "none";
      els.input.focus();
    }
  }

  function extractReply(data) {
    if (data == null) return "";
    return data.reply ?? data.answer ?? data.output ?? data.text ?? (
      typeof data === "string" ? data : JSON.stringify(data)
    );
  }

  async function sendMessage() {
    const text = els.input.value.trim();
    if (!text) return;
    els.input.disabled = true;
    els.send.disabled = true;
    addMessage(text, "you");
    if (CONFIG.simulateStreaming) addTyping();
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: CONFIG.headers,
        body: JSON.stringify({ question: text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const ct = res.headers.get("content-type") || "";
      let reply = "";
      if (ct.includes("application/json")) {
        reply = extractReply(await res.json());
      } else if (ct.includes("text/event-stream")) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let acc = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          acc += decoder.decode(value, { stream: true });
        }
        reply = acc.replace(/^data:\s*/gm, "").trim();
      } else {
        reply = await res.text();
      }
      if (CONFIG.simulateStreaming) removeTyping();
      addMessage(reply || "Sem conteúdo na resposta.", "bot");
    } catch (e) {
      if (CONFIG.simulateStreaming) removeTyping();
      addMessage("Ups, houve um erro a contactar o servidor. Verifica o endpoint em CONFIG.apiUrl.", "bot");
      console.error(e);
    } finally {
      els.input.disabled = false;
      els.send.disabled = false;
      els.input.value = "";
      els.input.focus();
    }
  }

  function pingBadge() {
    if (els.panel.style.display === "none" || els.panel.style.display === "") {
      els.badge.style.display = "flex";
      els.badge.textContent = "1";
    }
  }

  function makeDraggable() {
    let isDown = false, startX = 0, startY = 0, startLeft = 0, startTop = 0;
    const panel = els.panel, handle = els.header;
    const getRect = () => panel.getBoundingClientRect();
    handle.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".cb-btn")) return; // evita arrastar ao clicar no botão fechar
      isDown = true; panel.setPointerCapture(e.pointerId);
      const r = getRect();
      startX = e.clientX; startY = e.clientY;
      startLeft = r.left; startTop = r.top;
    });
    window.addEventListener("pointermove", (e) => {
      if (!isDown) return;
      const dx = e.clientX - startX, dy = e.clientY - startY;
      panel.style.right = "auto"; panel.style.bottom = "auto";
      const rect = getRect();
      panel.style.left = Math.max(8, Math.min(window.innerWidth - rect.width - 8, startLeft + dx)) + "px";
      panel.style.top = Math.max(8, Math.min(window.innerHeight - rect.height - 8, startTop + dy)) + "px";
    });
    window.addEventListener("pointerup", () => { isDown = false; });
  }

  function attachEvents(root) {
    els.launcher.addEventListener("click", () => togglePanel());
    els.close.addEventListener("click", () => togglePanel(false));
    els.send.addEventListener("click", sendMessage);
    els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") togglePanel(false);
});
    setTimeout(() => { pingBadge(); }, 2000);
  }
  

  function mount(target = document.body) {
    const container = document.createElement("div");
    container.id = "cb-root";
    container.innerHTML = markup();
    target.appendChild(container);
    els.launcher = qs("#cbLauncher", container);
    els.badge = qs("#cbBadge", container);
    els.panel = qs("#cbPanel", container);
    els.header = qs("#cbHeader", container);
    els.body = qs("#cbBody", container);
    els.input = qs("#cbInput", container);
    els.send = qs("#cbSend", container);
    els.close = qs("#cbClose", container);
    els.panel.style.display = "none";
    makeDraggable();
    attachEvents(container);
    qs("#cbSuggestions", container)?.addEventListener("click", (e) => {
      const chip = e.target.closest(".cb-chip");
      if (!chip) return;
      els.input.value = chip.getAttribute("data-q") || chip.textContent.trim();
      els.input.focus();
    });
  }

  function setConfig(partial) {
    if (partial && "apiUrl" in partial && partial.apiUrl !== CONFIG.apiUrl) {
      console.warn("[ChatbotBubble] Tentativa de override do apiUrl bloqueada:", partial.apiUrl);
      const { apiUrl, ...rest } = partial;
      Object.assign(CONFIG, rest);
    } else {
      Object.assign(CONFIG, partial || {});
    }
  }

  return { mount, setConfig };
})();
