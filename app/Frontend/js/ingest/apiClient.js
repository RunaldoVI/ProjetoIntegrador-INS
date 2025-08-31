window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  const BASE = "http://localhost:5000";

  async function jsonOrThrow(res) {
    const text = await res.text();
    if (!res.ok) throw new Error(`${res.status} ${text}`);
    return JSON.parse(text || "{}");
  }

  ns.apiClient = {
    async upload(formData) {
      const res = await fetch(`${BASE}/upload`, { method: "POST", body: formData });
      return jsonOrThrow(res);
    },
    async getPreviewItem(questionnaire, { ident=null, file=null } = {}) {
      let url = `${BASE}/outputs/${encodeURIComponent(questionnaire)}/item`;
      if (file) url += `?file=${encodeURIComponent(file)}`;
      else if (ident) url += `?ident=${encodeURIComponent(ident)}`;
      const res = await fetch(url);
      return jsonOrThrow(res);
    },
    async reprocessItem(questionnaire, { ident, file, instructions }) {
  const res = await fetch(`${BASE}/outputs/${encodeURIComponent(questionnaire)}/item/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ident, file, instructions })
  });
  return jsonOrThrow(res);
},
async logHistory({ email, nome_pdf, pdfFile = null }) {
  const fd = new FormData();
  fd.append("email", email);
  if (pdfFile) fd.append("pdf", pdfFile);
  else if (nome_pdf) fd.append("nome_pdf", nome_pdf);

  const res = await fetch(`${BASE}/api/user/upload_pdf`, { method: "POST", body: fd });
  return jsonOrThrow(res);
},
    async finalize(questionnaire) {
      const res = await fetch(`${BASE}/outputs/${encodeURIComponent(questionnaire)}/finalize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy: "use_preview_blocks" }),
      });
      return jsonOrThrow(res);
    },
    async getLogs(tail = 800) {
      const res = await fetch(`${BASE}/logs?tail=${tail}`);
      return res.json();
    },
  };
})(window.IngestHelpers);
