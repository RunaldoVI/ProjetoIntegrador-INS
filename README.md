# 📊 Projeto Integrador - INS  

Projeto desenvolvido para o **Projeto Integrador em Engenharia Informática (Instituto Piaget, Almada)**, com foco em **ingestão de documentos**, **extração automática de perguntas e respostas** e **geração dinâmica de questionários**.  
A solução combina **Processamento de Linguagem Natural (PLN)** com **Modelos de Linguagem de Grande Escala (LLMs)**, integrando **Python**, **Docker**, **MySQL** e o modelo **Mistral-7B** via **Ollama**.  

---

## 📌 Sumário  

- [🧠 Objetivo](#-objetivo)  
- [⚙️ Tecnologias Utilizadas](#️-tecnologias-utilizadas)  
- [📁 Estrutura do Projeto](#-estrutura-do-projeto)  
- [🚀 Como Executar Localmente](#-como-executar-localmente)  
- [📎 Exemplo de Uso](#-exemplo-de-uso)  
- [💬 Chatbot e FAQ](#-chatbot-e-faq)  
- [🛠️ Em Desenvolvimento](#️-em-desenvolvimento)  
- [🤝 Contribuições](#-contribuições)  
- [🧾 Licença](#-licença)  
- [📬 Contato](#-contato)  

---

## 🧠 Objetivo  

Automatizar a **extração, estruturação e reutilização de informação proveniente de documentos PDF** (ex.: questionários, relatórios), associando perguntas e respostas a identificadores únicos, com persistência em base de dados e exportação em formato **Excel**.  

O sistema ainda suporta a **criação automática de questionários dinâmicos** e oferece um **chatbot integrado** para apoio ao utilizador.  

---

## ⚙️ Tecnologias Utilizadas  

- 🐍 **Python 3.x** – backend e extração de dados  
- 🐳 **Docker / Docker Compose** – orquestração de serviços  
- 🧠 **Ollama + Mistral-7B** – modelo LLM local para análise semântica  
- 🐬 **MySQL** – base de dados relacional  
- 🌐 **HTML + Tailwind CSS + JavaScript** – frontend responsivo  
- 📊 **Pandas, OpenPyXL, ReportLab** – manipulação de dados e relatórios  
- 🔐 **dotenv** – gestão de variáveis de ambiente  

---

## 📁 Estrutura do Projeto  

ProjetoIntegrador-INS/
│
├── app/ # Código-fonte principal
│ ├── Backend/ # Extração e análise de PDFs, integração com LLM
│ ├── Frontend/ # HTML, CSS, JS (UI, autenticação, chatbot, dropzone)
│ ├── Database/ # Esquemas e scripts MySQL
│ └── api/ # API REST em Python
│
├── mysql-init/ # Scripts de inicialização do MySQL
├── pdfs-excels/ # PDFs de entrada e Excels exportados
├── ProjetoFinal.py # Script principal do pipeline
├── requirements.txt # Dependências Python
├── Dockerfile # Docker do backend
├── Dockerfile.api # Docker da API
├── docker-compose.yml # Orquestração dos serviços
├── startup.sh # Script de inicialização
└── README.md # Este ficheiro

---

## 🚀 Como Executar Localmente

### 1. Clone o repositório


git clone https://github.com/Custodio30/ProjetoIntegrador-INS.git
cd ProjetoIntegrador-INS

### 1. Fazer compose 

docker compose up --build

Ao correr o prompt no terminal vai ter tudo o que for preciso para correr o programa na sua máquina

### 2. Suba os serviços com Docker Compose

docker compose up --build

Isso irá iniciar automaticamente:

Frontend (Nginx, porta 8080)
API backend (Python, porta 5000)
Serviço de processamento (PDF → LLM)
Base de dados MySQL (porta 3307 no host)
Ollama com Mistral (porta 11434)
qdrant(porta 6333)

### 3. Aceda à aplicação

Abra no navegador:
http://localhost:8080

## 📎 Exemplo de Uso

1.Registe uma conta ou faça login.

2.Vá a Ingestão / Upload e carregue um ficheiro PDF.

3.Escolha entre os modos:

4.Preview → mostra pré-visualização dos blocos (perguntas/respostas).

5.Automático → processa diretamente e gera Excel.

6.Acompanhe o progresso do processamento.

7.Faça download do Excel estruturado.

8.Consulte o histórico de uploads no perfil.

## 💬 Chatbot e FAQ

O sistema inclui um chatbot integrado, acessível através da interface, que responde a dúvidas comuns:

1.Como criar conta ou iniciar sessão

2.Diferença entre modos Preview e Automático

3.Onde descarregar o Excel

4.O que são identificadores das perguntas

5.Como funciona o histórico e a gestão de dados

📖 Também podes consultar o FAQ Completo incluído no relatório.

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

### Licença
🧾 Licença
Este projeto está licenciado sob a MIT License. Veja o arquivo LICENSE para mais detalhes.

### Contato
📬 Contato
Desenvolvedor: joao custodio
E-mail: joaocustodio30@gmail.com
LinkedIn: https://www.linkedin.com/in/jo%C3%A3o-cust%C3%B3dio30/

Desenvolvedor: Ronaldo Ribalonga
E-mail: ronaldoribalonga@gmail.com
LinkedIn: https://www.linkedin.com/in/ronaldo-ribalonga-190a03233/ 

Desenvolvedor: Rodrigo Vicente
E-mail: rodrigo.vicente260204@gmail.com
LinkdIn: https://www.linkedin.com/in/rodrigo-vicente-670a98270
