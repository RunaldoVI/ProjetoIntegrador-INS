# Backend/Chatbot/qdrant_index.py
import argparse
from pathlib import Path
import os
import uuid
from typing import List, Dict, Any

import mysql.connector
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import TextLoader  # (PDF opcional, ver notas)
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain.schema import Document

from Backend.Chatbot.qdrant_config import (
    OLLAMA_BASE_URL, QDRANT_URL,
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
    EMB_MODEL, TABLES,
    REPO_ROOT, REPO_GLOBS, COLLECTION_REPO,
    COLLECTION_USERKB, USERKB_DIR
)

# ------------- BD -------------
def db_conn():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME, autocommit=True
    )

def fetch_rows(table_cfg: Dict[str, str], limit: int | None = None) -> List[Dict[str, Any]]:
    table = table_cfg["table"]
    id_col = table_cfg["id_col"]
    text_col = table_cfg["text_col"]
    ident_q = table_cfg["identificador_pergunta_col"]
    ident_sem = table_cfg["identificador_semantico_col"]

    sql = f"""
        SELECT
          `{id_col}` AS id,
          `{text_col}` AS texto,
          `{ident_q}` AS identificador_pergunta,
          `{ident_sem}` AS identificador_semantico
        FROM `{table}`
        WHERE `{text_col}` IS NOT NULL AND TRIM(`{text_col}`) <> ''
        ORDER BY `{id_col}` ASC
    """
    if limit:
        sql += f" LIMIT {int(limit)}"

    cn = db_conn()
    cur = cn.cursor(dictionary=True)
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close(); cn.close()
    return rows

# ------------------ User KB -----------------------
def _load_userkb_docs(root: str) -> list[Document]:
    rootp = Path(root)
    docs: list[Document] = []
    if not rootp.exists():
        return docs
    for p in rootp.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
            for d in TextLoader(str(p), encoding="utf-8", autodetect_encoding=True).load():
                d.metadata["path"] = str(p.relative_to(rootp))
                docs.append(d)
    return docs

def index_userkb(client: QdrantClient, emb: OllamaEmbeddings, root: str, collection: str, batch: int = 64):
    # Garantir coleção mesmo sem docs
    dim = len(emb.embed_query("probe"))
    ensure_collection(client, collection, vector_size=dim)

    docs = _load_userkb_docs(root)
    if not docs:
        print(f"[userkb] nada para indexar (coleção '{collection}' criada vazia).")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    points, sent = [], 0
    print(f"[userkb] {len(docs)} docs → coleção '{collection}'")

    for d in docs:
        chunks = splitter.split_text(d.page_content)
        for i, ch in enumerate(chunks):
            vec = emb.embed_query(ch)
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"userkb:{d.metadata['path']}#{i}"))
            payload = {"table":"userkb", "path": d.metadata["path"], "texto": ch, "title": d.metadata["path"]}
            points.append(qm.PointStruct(id=pid, vector=vec, payload=payload))
            if len(points) >= batch:
                client.upsert(collection_name=collection, points=points, wait=True)
                sent += len(points); points = []
    if points:
        client.upsert(collection_name=collection, points=points, wait=True); sent += len(points)
    print(f"[userkb] done ✔ ({sent} chunks)")


# ------------- Qdrant helpers -------------
def ensure_collection(client: QdrantClient, name: str, vector_size: int):
    try:
        client.get_collection(name)
        return
    except Exception:
        pass
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE)
    )

def batched(it, size: int):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

# ------------- Indexar tabelas (perguntas/respostas) -------------
def index_table(client: QdrantClient, emb: OllamaEmbeddings, key: str, limit: int | None, batch: int):
    cfg = TABLES[key]

    # 1) garantir coleção (mesmo vazia)
    dim = len(emb.embed_query("probe"))
    collection = cfg["collection"]
    ensure_collection(client, collection, vector_size=dim)

    # 2) só depois ir buscar linhas
    rows = fetch_rows(cfg, limit=limit)
    if not rows:
        print(f"[{key}] nada para indexar (coleção '{collection}' criada vazia).")
        return

    print(f"[{key}] {len(rows)} registos → coleção '{collection}' (batch={batch})")
    sent = 0
    for chunk in batched(rows, batch):
        texts = [r["texto"] for r in chunk]
        vectors = emb.embed_documents(texts)
        points = []
        for r, v in zip(chunk, vectors):
            pid = int(r["id"])  # Qdrant aceita int ou UUID
            payload = {
                "table": cfg["table"],
                "row_id": r["id"],
                "texto": r["texto"],
                "identificador_pergunta": r["identificador_pergunta"],
                "identificador_semantico": r["identificador_semantico"],
            }
            points.append(qm.PointStruct(id=pid, vector=v, payload=payload))
        client.upsert(collection_name=collection, points=points, wait=True)
        sent += len(points)
        print(f"  -> {sent}/{len(rows)}")
    print(f"[{key}] done ✔")

# ------------- Indexar repositório (código + docs) -------------
EXCLUDE_DIRS = {".git","__pycache__","node_modules","dist","build",".venv",".mypy_cache"}
INCLUDE_EXTS = {".py",".md",".txt",".sql",".java",".html",".js",".css"}

def _should_index(p: Path) -> bool:
    return (
        p.is_file()
        and p.suffix.lower() in INCLUDE_EXTS
        and not any(d in EXCLUDE_DIRS for d in p.parts)
    )

def _splitter_for(p: Path):
    ext = p.suffix.lower()
    if ext == ".py":
        return RecursiveCharacterTextSplitter.from_language(Language.PYTHON, chunk_size=800, chunk_overlap=80)
    if ext == ".java":
        return RecursiveCharacterTextSplitter.from_language(Language.JAVA, chunk_size=800, chunk_overlap=80)
    if ext == ".md":
        return RecursiveCharacterTextSplitter.from_language(Language.MARKDOWN, chunk_size=1200, chunk_overlap=150)
    return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)

def load_repo_chunks(root: str, patterns: List[str]) -> List[Document]:
    rootp = Path(root)
    raw_docs: List[Document] = []
    for pat in patterns:
        for p in rootp.glob(pat.strip()):
            if not _should_index(p):
                continue
            # Só texto (rápido e sem novas deps). Para PDF, ver nota em baixo.
            for d in TextLoader(str(p), encoding="utf-8", autodetect_encoding=True).load():
                d.metadata["path"] = str(p.relative_to(rootp))
                raw_docs.append(d)

    chunks: List[Document] = []
    for d in raw_docs:
        path = Path(d.metadata["path"])
        splitter = _splitter_for(path)
        for part in splitter.split_text(d.page_content):
            chunks.append(Document(page_content=part, metadata={"path": d.metadata["path"]}))
    return chunks

def index_repo(client: QdrantClient, emb: OllamaEmbeddings, root: str, patterns: List[str], collection: str, batch: int):
    # Garantir coleção mesmo sem docs
    dim = len(emb.embed_query("probe"))
    ensure_collection(client, collection, vector_size=dim)

    docs = load_repo_chunks(root, patterns)
    if not docs:
        print(f"[repo] nada para indexar (coleção '{collection}' criada vazia).")
        return

    print(f"[repo] {len(docs)} chunks → coleção '{collection}' (batch={batch})")

    # Embedding em lotes para reduzir chamadas ao Ollama
    sent = 0
    for chunk in batched(docs, batch):
        texts = [d.page_content for d in chunk]
        vectors = emb.embed_documents(texts)
        points = []
        for d, v in zip(chunk, vectors):
            key = f"{d.metadata.get('path','unknown')}#{sent}"
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, key))  # UUID determinístico
            payload = {"table": "repo", "path": d.metadata.get("path"), "texto": d.page_content}
            points.append(qm.PointStruct(id=pid, vector=v, payload=payload))
            sent += 1
        client.upsert(collection_name=collection, points=points, wait=True)

    print("[repo] done ✔")

# ------------- CLI -------------
def main():
    ap = argparse.ArgumentParser(
        description="Indexa perguntas/respostas, repositório e/ou documentação de utilizador no Qdrant via Ollama embeddings."
    )
    ap.add_argument(
        "--targets",
        default="perguntas,respostas,repo,userkb",
        help="ex.: perguntas,respostas | repo | userkb | perguntas,respostas,repo,userkb"
    )
    ap.add_argument("--limit", type=int, default=None, help="limitar nº de linhas (tabelas) p/ teste")
    ap.add_argument("--batch", type=int, default=64, help="tamanho do lote para upsert/embeddings")
    args = ap.parse_args()

    client = QdrantClient(url=QDRANT_URL)
    emb = OllamaEmbeddings(model=EMB_MODEL, base_url=OLLAMA_BASE_URL)

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    for t in targets:
        if t == "repo":
            index_repo(client, emb, REPO_ROOT, REPO_GLOBS, collection=COLLECTION_REPO, batch=args.batch)
            continue
        if t == "userkb":
            index_userkb(client, emb, USERKB_DIR, collection=COLLECTION_USERKB, batch=args.batch)
            continue
        if t not in TABLES:
            print(f"[skip] alvo desconhecido: {t}")
            continue
        index_table(client, emb, t, limit=args.limit, batch=args.batch)

if __name__ == "__main__":
    main()
