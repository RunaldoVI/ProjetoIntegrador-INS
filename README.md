# 📊 Projeto Integrador - INS

Projeto desenvolvido para o **Projeto Integrador da UNIVESP**, com foco em **automação de relatórios**, **análise de dados** e **integração com modelos de linguagem** (LLMs) utilizando **Python**, **Docker**, **MySQL** e o modelo **Mistral-7B** via **Ollama**.

---

## 📌 Sumário

- [📊 Projeto Integrador - INS](#-projeto-integrador---ins)
  - [📌 Sumário](#-sumário)
  - [🧠 Objetivo](#-objetivo)
  - [⚙️ Tecnologias Utilizadas](#️-tecnologias-utilizadas)
  - [📁 Estrutura do Projeto](#-estrutura-do-projeto)
  - [🚀 Como Executar Localmente](#-como-executar-localmente)
  - [📎 Exemplo de Uso](#-exemplo-de-uso)
  - [🛠️ Em Desenvolvimento](#️-em-desenvolvimento)
  - [🤝 Contribuições](#-contribuições)
  - [🧾 Licença](#-licença)
  - [📬 Contato](#-contato)

---

## 🧠 Objetivo

Automatizar a geração de relatórios baseados em dados de entrada (como planilhas Excel e PDFs), utilizando **modelos de linguagem natural (LLMs)** para processamento e análise inteligente, com interface de terminal e suporte a persistência em banco de dados.

---

## ⚙️ Tecnologias Utilizadas

- 🐍 **Python 3.x**
- 🐳 **Docker / Docker Compose**
- 🧠 **Ollama + Mistral-7B** (modelo LLM local)
- 🐬 **MySQL**
- 📊 **Pandas, OpenPyXL, ReportLab** (manipulação de dados e geração de relatórios)
- 🔐 **dotenv** (gerenciamento de variáveis de ambiente)

---

## 📁 Estrutura do Projeto

ProjetoIntegrador-INS/
│
├── app/ # Código-fonte principal
├── pdfs-excels/ # Documentos de entrada (Excel, PDF)
├── mysql-init/ # Scripts de inicialização do MySQL
├── Dockerfile # Docker para o app
├── Dockerfile.api # Docker para API (em progresso)
├── docker-compose.yml # Orquestração dos contêineres
├── ProjetoFinal.py # Script principal
├── requirements.txt # Dependências Python
├── startup.sh # Script de inicialização automatizada
└── things_to_do.txt # Lista de tarefas/pendências


---

## 🚀 Como Executar Localmente

### 1. Clone o repositório


git clone https://github.com/Custodio30/ProjetoIntegrador-INS.git
cd ProjetoIntegrador-INS

### 1. Fazer compose 

docker compose up --build

ao fazer isto vai ter tudo disponivel para correr o programa na sua máquina

### Contriubuições

Contribuições são bem-vindas! Para contribuir:

Faça um fork do projeto

Crie uma branch com sua feature:

bash
Copy
Edit
git checkout -b minha-feature
Commit suas mudanças:

bash
Copy
Edit
git commit -m 'feat: adicionei nova funcionalidade'
Envie o push para sua branch:

bash
Copy
Edit
git push origin minha-feature
Abra um Pull Request

🧾 Licença
Este projeto está licenciado sob a MIT License. Veja o arquivo LICENSE para mais detalhes.

📬 Contato
Desenvolvedor: joao custodio
E-mail: joaocustodio30@gmail.com
LinkedIn: https://www.linkedin.com/in/jo%C3%A3o-cust%C3%B3dio30/

Desenvolvedor: Ronaldo Ribalonga
E-mail: ronaldoribalonga@gmail.com
LinkedIn: https://www.linkedin.com/in/ronaldo-ribalonga-190a03233/ 