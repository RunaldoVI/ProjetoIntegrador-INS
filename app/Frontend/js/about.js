document.addEventListener("DOMContentLoaded", () => {
  const section = document.querySelector(".section");

  if (!section) {
    console.warn("Seção 'Sobre' não encontrada.");
    return;
  }

  // Aqui você pode futuramente adicionar interações ou animações extras
  console.log("Seção 'Sobre' carregada com sucesso.");
});
