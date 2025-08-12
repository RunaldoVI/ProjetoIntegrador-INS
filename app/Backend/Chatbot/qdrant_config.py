# backend/Chatbot/qdrant_config.py
import os

# ---- Serviços (vêm do .env via docker-compose) ----
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
QDRANT_URL      = os.getenv("QDRANT_URL", "http://qdrant:6333")

# ---- Modelos ----
CHAT_MODEL = os.getenv("CHAT_MODEL", "mistral")
EMB_MODEL  = os.getenv("EMB_MODEL", "nomic-embed-text")
EMB_DIM    = int(os.getenv("EMB_DIM", "768"))
TOPK       = int(os.getenv("TOPK", "5"))

# ---- MySQL (usa o nome do serviço interno) ----
DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = int(os.getenv("DB_PORT", "3306"))  # porta interna do serviço
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "projetofinal_ins")

# ---- Coleções do Qdrant ----
COLLECTION_PERGUNTAS = os.getenv("COLLECTION_PERGUNTAS", "perguntas_collection")
COLLECTION_RESPOSTAS = os.getenv("COLLECTION_RESPOSTAS", "respostas_collection")

# --- Coleção e fontes do repositório ---
COLLECTION_REPO = os.getenv("COLLECTION_REPO", "repo_collection")

# Raiz do projeto dentro do container e padrões de ficheiros a indexar
REPO_ROOT = os.getenv("REPO_ROOT", "/app")
REPO_GLOBS = os.getenv("REPO_GLOBS",
    "Backend/**/*.py,Backend/**/*.md,Frontend/**/*.md,Frontend/**/*.html,Frontend/**/*.js,Frontend/**/*.css,README.md,**/*.sql").split(",")

# --- Documentação de utilizador (User KB) ---
COLLECTION_USERKB = os.getenv("COLLECTION_USERKB", "user_kb")
USERKB_DIR = os.getenv("USERKB_DIR", "/app/docs/publico")

# ---- Tabelas/colunas a indexar ----
# Atenção: colunas com hífen precisam de backticks no SQL (`identificador-pergunta`)
TABLES = {
    "perguntas": {
        "table": "perguntas",
        "id_col": "id",
        "text_col": "texto",
        "identificador_pergunta_col": "identificador-pergunta",
        "identificador_semantico_col": "identificador-semantico",
        "collection": COLLECTION_PERGUNTAS,
    },
    "respostas": {
        "table": "respostas",
        "id_col": "id",
        "text_col": "texto",
        "identificador_pergunta_col": "identificador-pergunta",
        "identificador_semantico_col": "identificador-semantico",
        "collection": COLLECTION_RESPOSTAS,
    },
}
