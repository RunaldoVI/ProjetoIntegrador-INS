document.addEventListener("DOMContentLoaded", () => {
  const user = JSON.parse(localStorage.getItem("user"));

  if (!user || !user.email) {
    window.location.href = "login.html";
    return;
  }

  const historyList = document.getElementById("pdf-history");

  fetch(`http://localhost:5000/api/user/profile?email=${encodeURIComponent(user.email)}`)
    .then((res) => {
      if (!res.ok) throw new Error("Erro ao carregar histórico.");
      return res.json();
    })
    .then((dados) => {
      historyList.innerHTML = "";

      if (dados.pdfs && dados.pdfs.length > 0) {
        dados.pdfs.forEach((pdf) => {
          const li = document.createElement("li");
          li.innerHTML = `${pdf.nome} <span class="text-xs text-gray-400">(${pdf.data})</span>`;
          historyList.appendChild(li);
        });
      } else {
        historyList.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
      }
    })
    .catch((err) => {
      console.error("Erro ao carregar PDFs:", err);
      historyList.innerHTML = `<li class="text-red-500">Erro ao carregar histórico.</li>`;
    });
});

