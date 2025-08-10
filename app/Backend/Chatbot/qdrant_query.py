# backend/Chatbot/qdrant_query.py
from typing import List, Dict, Any
import os
from qdrant_client import QdrantClient
from langchain_ollama import OllamaEmbeddings, ChatOllama

from Backend.Chatbot.qdrant_config import (
    OLLAMA_BASE_URL, QDRANT_URL,
    CHAT_MODEL, EMB_MODEL, TOPK,
    COLLECTION_PERGUNTAS, COLLECTION_RESPOSTAS, COLLECTION_REPO
)

# Opcional: coleção de documentação de utilizador (se existir na config)
try:
    from Backend.Chatbot.qdrant_config import COLLECTION_USERKB  # user_kb
except Exception:
    COLLECTION_USERKB = None  # segue sem user_kb

# ------- Parâmetros de controlo por .env -------
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.40"))
OUT_OF_SCOPE_MSG = os.getenv(
    "OUT_OF_SCOPE_MSG",
    "Este assistente responde apenas a perguntas sobre o Projeto Integrador. Não encontro relação com o contexto indexado."
)
BLOCK_DEV_QUESTIONS = os.getenv("BLOCK_DEV_QUESTIONS", "1") == "1"
DEV_KEYWORDS = {
    "classe","endpoint","controller","service","package","import","def","function",
    "ficheiro","arquivo","path","stack","trace","stacktrace","docker","compose",
    "sql","schema","código","codigo","api route","rota","framework","método","metodo"
}

# ------- Modelos / clientes -------
_qdrant = QdrantClient(url=QDRANT_URL)
_emb = OllamaEmbeddings(model=EMB_MODEL, base_url=OLLAMA_BASE_URL)
_llm = ChatOllama(model=CHAT_MODEL, temperature=0, base_url=OLLAMA_BASE_URL)

SYSTEM = (
    "És um assistente do Projeto Integrador para UTILIZADORES FINAIS. "
    "Responde APENAS a perguntas relacionadas com o Projeto Integrador e SOMENTE com base no CONTEXTO fornecido. "
    f"Se a pergunta não estiver relacionada com o projeto ou o contexto não suportar uma resposta, responde exatamente: '{OUT_OF_SCOPE_MSG}'. "
    "Não reveles código, nomes de ficheiros, caminhos ou jargão técnico. Usa linguagem simples, prática e orientada a tarefas."
)

# ------- Helpers -------
def _is_dev_question(q: str) -> bool:
    if not BLOCK_DEV_QUESTIONS:
        return False
    t = q.lower()
    return any(k in t for k in DEV_KEYWORDS)

def _search_collection(question: str, collection: str, k: int) -> List[Dict[str, Any]]:
    qvec = _emb.embed_query(question)
    hits = _qdrant.search(
        collection_name=collection,
        query_vector=qvec,
        limit=k,
        with_payload=True,
    )
    out: List[Dict[str, Any]] = []
    for h in hits:
        p = h.payload or {}
        out.append({
            "id": h.id,
            "score": float(h.score),
            "table": p.get("table"),
            "row_id": p.get("row_id"),
            "texto": p.get("texto", "") or "",
            "path": p.get("path"),
        })
    return out

def retrieve(question: str, k: int = TOPK) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []

    # 1) Prioriza documentação de utilizador (se existir)
    if COLLECTION_USERKB:
        hits += _search_collection(question, COLLECTION_USERKB, k * 2)

    # 2) Complementa com BD (perguntas/respostas) e, por fim, repo (conteúdos técnicos)
    hits += _search_collection(question, COLLECTION_PERGUNTAS, max(1, k // 2))
    hits += _search_collection(question, COLLECTION_RESPOSTAS, max(1, k // 2))
    # repo é útil para conceitos, mas não mostramos caminhos ao utilizador
    hits += _search_collection(question, COLLECTION_REPO, max(1, k // 2))

    # Ordena por score e aplica limiar + corta a k
    hits = sorted(hits, key=lambda x: x["score"], reverse=True)
    hits = [h for h in hits if h["score"] >= MIN_SCORE]
    return hits[:k]

def _build_context(chunks: List[Dict[str, Any]]) -> str:
    # Não expõe caminhos/IDs; só o texto. Mantém indices [1], [2]...
    parts = []
    for i, c in enumerate(chunks, 1):
        text = (c.get("texto") or "").strip()
        if len(text) > 1200:
            text = text[:1200] + "..."
        parts.append(f"[{i}] {text}")
    return "\n\n".join(parts)

def _public_ref(_: Dict[str, Any]) -> str:
    # Mostramos referências genéricas; sem caminhos/IDs
    return "Base de conhecimento do projeto"

# ------- API principal -------
def answer_question(question: str, k: int = TOPK) -> Dict[str, Any]:
    # Gate 1: bloquear perguntas de desenvolvimento
    if _is_dev_question(question):
        return {
            "answer": "Este assistente é focado no uso da aplicação. Para questões técnicas de desenvolvimento, contacta a equipa técnica.",
            "sources": []
        }

    # Recuperação por relevância
    chunks = retrieve(question, k=k)

    # Gate 2: fora de escopo / sem contexto suficiente
    if not chunks:
        return {"answer": OUT_OF_SCOPE_MSG, "sources": []}

    # Geração com contexto
    context = _build_context(chunks)
    prompt = (
        f"PERGUNTA DO UTILIZADOR: {question}\n\n"
        f"CONTEXTO (não mostrar metadados ao utilizador):\n{context}\n\n"
        "Responde de forma clara e breve para utilizadores finais. "
        "Se algo não estiver no contexto, diz que não encontras essa informação no contexto."
    )

    msg = _llm.invoke([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ])

    # Referências genéricas (sem caminhos/IDs)
    sources = [{"ref": _public_ref(c), "score": c["score"]} for c in chunks]

    return {"answer": getattr(msg, "content", str(msg)), "sources": sources}
