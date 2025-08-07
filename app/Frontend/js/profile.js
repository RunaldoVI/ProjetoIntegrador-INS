// Função para carregar o perfil
function loadProfile() {
  const user = JSON.parse(localStorage.getItem("user"));
  if (!user || !user.email) {
    window.location.href = "sections/login.html";
    return;
  }

  fetch(`http://localhost:5000/api/user/profile?email=${encodeURIComponent(user.email)}`)
    .then((res) => {
      if (!res.ok) throw new Error("Erro ao carregar perfil");
      return res.json();
    })
    .then((dados) => {
      // Preencher perfil
      document.getElementById("user-name").textContent = dados.nome || "—";
      document.getElementById("user-info").textContent = `Utilizador registado com o email ${dados.email || "—"}`;
      document.getElementById("profile-nome").textContent = dados.nome || "—";
      document.getElementById("profile-email").textContent = dados.email || "—";
      document.getElementById("profile-funcao").textContent = dados.funcao || "—";
      document.getElementById("profile-inst").textContent = dados.instituicao || "—";

      const avatarImg = document.getElementById("user-avatar");
      avatarImg.src = `http://localhost:5000/uploads/avatars/${dados.avatar || "default.png"}`;
      avatarImg.onerror = () => {
        avatarImg.src = "http://localhost:5000/uploads/avatars/default.png";
      };

      // Guardar dados no localStorage
      localStorage.setItem("user", JSON.stringify(dados));
      carregarHistoricoPDFs();
    })
    .catch((err) => {
      console.error("Erro ao carregar perfil:", err);
    });

  // Modal lógica
  const btnEditar = document.getElementById("btnEditarPerfil");
  const modal = document.getElementById("editModal");
  const modalContent = document.getElementById("editModalContent");
  const btnCancelar = document.getElementById("btnCancelar");
  const btnGuardar = document.getElementById("btnGuardar");

  let avatarBase64 = ""; // Variável para guardar o novo avatar

  // Evento de clique para abrir o modal
  btnEditar.addEventListener("click", () => {
    const user = JSON.parse(localStorage.getItem("user"));
    if (user) {
      document.getElementById("editNome").value = user.nome || "";
      document.getElementById("editEmail").value = user.email || "";
      document.getElementById("editFuncao").value = user.funcao || "";
      document.getElementById("editInstituicao").value = user.instituicao || "";

      const preview = document.getElementById("avatarPreview");
      preview.src = `http://localhost:5000/uploads/avatars/${user.avatar || "default.png"}`;
    }

    // Tornar o modal visível com animação
    modal.classList.remove("hidden");
    modal.classList.add("bg-opacity-60");
    setTimeout(() => {
      modalContent.classList.add("scale-100", "opacity-100");
      modalContent.classList.remove("scale-95", "opacity-0");
    }, 10);
  });

  // Função para fechar o modal
  function fecharModal() {
    modal.classList.remove("bg-opacity-60");
    modalContent.classList.remove("scale-100", "opacity-100");
    modalContent.classList.add("scale-95", "opacity-0");
    setTimeout(() => {
      modal.classList.add("hidden");
    }, 300); // Esconde o modal após a animação
  }

  // Fechar o modal ao clicar no botão "Cancelar"
  btnCancelar.addEventListener("click", fecharModal);
  
  // Fechar o modal ao clicar fora dele
  modal.addEventListener("click", (e) => {
    if (e.target === modal) fecharModal();
  });

  // Ler novo avatar
  document.getElementById("editAvatar").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validação: apenas JPG ou PNG
      if (!["image/jpeg", "image/png"].includes(file.type)) {
        alert("Apenas imagens JPG ou PNG são permitidas.");
        e.target.value = "";
        return;
      }

      // Validação: tamanho máximo 5MB
      if (file.size > 3 * 1024 * 1024) {
        alert("A imagem deve ter no máximo 3MB.");
        e.target.value = "";
        return;
      }

      // Mostrar preview
      const reader = new FileReader();
      reader.onload = function(event) {
        avatarBase64 = event.target.result;
        document.getElementById("avatarPreview").src = avatarBase64;
      };
      reader.readAsDataURL(file);
    }
  });

  // Submeter os dados do perfil
btnGuardar.addEventListener("click", () => {
  const nome = document.getElementById("editNome").value.trim();
  const email = document.getElementById("editEmail").value.trim();
  const funcao = document.getElementById("editFuncao").value.trim();
  const instituicao = document.getElementById("editInstituicao").value.trim();
  const avatarFile = document.getElementById("editAvatar").files[0]; // ficheiro selecionado

  const formData = new FormData();

  // Verificar se o nome foi alterado
  if (nome) formData.append("nome", nome);

  // Verificar se o email foi alterado
  if (email) formData.append("email", email);

  // Verificar se a função foi alterada
  if (funcao) formData.append("funcao", funcao);

  // Verificar se a instituição foi alterada
  if (instituicao) formData.append("instituicao", instituicao);

  // Adiciona avatar apenas se um arquivo foi selecionado
  if (avatarFile) {
    formData.append("avatar", avatarFile); // Se o avatar for fornecido
  }

  // Verificar se algum campo foi modificado antes de enviar
  if (formData.has("nome") || formData.has("email") || formData.has("funcao") || formData.has("instituicao") || formData.has("avatar")) {
    fetch("http://localhost:5000/api/user/profile", {
      method: "PUT", // Método PUT para atualizar o perfil
      body: formData, // Corpo com FormData
    })
      .then(res => {
        if (!res.ok) throw new Error("Erro ao guardar perfil");
        return res.json();
      })
      .then(data => {
        localStorage.setItem("user", JSON.stringify(data)); // Atualiza dados no localStorage
        console.log("Perfil atualizado com sucesso:", data);
        fecharModal();
        location.reload(); // Atualiza perfil visível
      })
      .catch(err => {
        console.error("Erro ao guardar perfil:", err); // Caso algum erro ocorra
      });
  } else {
    console.log("Nenhum campo foi alterado."); // Caso não tenha modificado nada
  }
});
}

  function togglePassword() {
  const passwordField = document.getElementById("editPassword");
  const passwordIcon = document.getElementById("togglePasswordIcon");

  // Verificar o tipo do campo de senha
  if (passwordField.type === "password") {
    passwordField.type = "text";
    passwordIcon.classList.remove("fa-eye");
    passwordIcon.classList.add("fa-eye-slash");
  } else {
    passwordField.type = "password";
    passwordIcon.classList.remove("fa-eye-slash");
    passwordIcon.classList.add("fa-eye");
  }
}

function carregarHistoricoPDFs() {
  const user = JSON.parse(localStorage.getItem("user"));
  const lista = document.getElementById("pdf-history");

  if (!user || !user.email || !lista) {
    lista.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
    return;
  }

  fetch(`http://localhost:5000/api/user/historico?email=${encodeURIComponent(user.email)}`)
    .then(res => res.json())
    .then(data => {
      if (data.historico && data.historico.length > 0) {
        const items = data.historico.map(item => `
          <li class="flex items-center justify-between">
            <span>📄 ${item.nome}</span>
            <span class="text-xs text-gray-500">${item.data}</span>
          </li>
        `).join("");
        lista.innerHTML = items;
      } else {
        lista.innerHTML = "<li>Nenhum PDF ingerido ainda.</li>";
      }
    })
    .catch(err => {
      console.error("Erro ao carregar histórico de PDFs:", err);
      lista.innerHTML = "<li>Erro ao carregar histórico.</li>";
    });
}

document.addEventListener("DOMContentLoaded", () => {
  loadProfile();
});
