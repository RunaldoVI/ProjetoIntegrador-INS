async function verificarLLM() {
  try {
    const res = await fetch("http://localhost:5000/llm-status");
    const data = await res.json();
    const overlay = document.getElementById("llm-loading-overlay");

    if (!data.ready) {
      overlay?.classList.remove("hidden");
      document.body.style.overflow = "hidden";
      monitorLLMProgress();
    } else {
      overlay?.classList.add("hidden");
      document.body.style.overflow = "";
    }
  } catch (e) {
    console.error("Erro ao verificar LLM:", e);
    monitorLLMProgress();
  }
}

async function monitorLLMProgress() {
  const overlay = document.getElementById("llm-loading-overlay");
  const progressText = document.getElementById("llm-progress-text");
  const progressBar = document.getElementById("llm-progress-bar");

  overlay?.classList.remove("hidden");
  document.body.style.overflow = "hidden";

  let ready = false;

  while (!ready) {
    try {
      const [statusRes, progressRes] = await Promise.all([
        fetch("http://localhost:5000/llm-status"),
        fetch("http://localhost:5000/llm-progress")
      ]);

      const status = await statusRes.json();
      const progress = await progressRes.json();
      ready = status.ready;

      const percent = progress.progress || 0;
      if (progressText) progressText.innerText = `${percent.toFixed(1)}%`;
      if (progressBar) progressBar.style.width = `${percent}%`;
    } catch (err) {
      console.error("Erro ao obter progresso/status:", err);
    }

    await new Promise(resolve => setTimeout(resolve, 1500));
  }

  overlay?.classList.add("hidden");
  document.body.style.overflow = "";
}

window.addEventListener("load", verificarLLM);
