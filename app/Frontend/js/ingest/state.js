window.IngestHelpers = window.IngestHelpers || {};

(function (ns) {
  ns.state = {
    processingMode: localStorage.getItem("modo") || "automatico",
    isAnalyzing: false,
    currentPdfFile: null,
    nav: { questionnaire: null, ident: null, file: null },
  };

  ns.session = {
    set(key, val) { sessionStorage.setItem(key, val); },
    get(key) { return sessionStorage.getItem(key); },
    del(key) { sessionStorage.removeItem(key); }
  };

  ns.setProcessingMode = (mode) => {
    ns.state.processingMode = mode;
    localStorage.setItem("modo", mode);
  };

  ns.setNav = (questionnaire, ident, file) => {
    ns.state.nav = { questionnaire, ident, file };
  };
})(window.IngestHelpers);
