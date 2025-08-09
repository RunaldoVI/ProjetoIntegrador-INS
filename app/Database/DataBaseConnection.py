import re
import mysql.connector
import json
import os
import sys
from sentence_transformers import SentenceTransformer, util
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Backend', 'SemanticComparison')))
from SemanticQuestionComparison import limpar_texto, atribuir_identificador

def conectar_bd():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "projetofinal_ins")
    )

ID_REGEX = re.compile(r"\b[A-Z]{2,}\.\d{3}\b")  # ex.: DPQ.010, DUQ.230

def extrair_ident_pergunta(pergunta_raw, entrada):
    ident = (entrada.get("identificador")
             or entrada.get("Identificador")
             or entrada.get("id")
             or entrada.get("ID"))
    if ident:
        return ident.strip()
    if pergunta_raw:
        m = ID_REGEX.search(pergunta_raw)
        if m:
            return m.group(0)
    return None

def importar_json_para_bd(caminho_json):
    conn = conectar_bd()
    cursor = conn.cursor()

    # --- carregar memória para agrupar semanticamente ---
    cursor.execute("SELECT texto, `identificador-semantico` FROM perguntas")
    dados_bd = cursor.fetchall()
    perguntas_bd = [limpar_texto(p[0]) for p in dados_bd]
    perguntas_sem_ids = [p[1] for p in dados_bd]

    cursor.execute("SELECT COALESCE(MAX(`identificador-semantico`), 0) FROM perguntas")
    proximo_sem_pergunta = (cursor.fetchone()[0] or 0) + 1

    cursor.execute("SELECT texto, `identificador-semantico` FROM respostas")
    respostas_raw = cursor.fetchall()
    respostas_bd = [limpar_texto(r[0]) for r in respostas_raw]
    respostas_sem_ids = [r[1] for r in respostas_raw]

    cursor.execute("SELECT COALESCE(MAX(`identificador-semantico`), 0) FROM respostas")
    proximo_sem_resposta = (cursor.fetchone()[0] or 0) + 1

    modelo = SentenceTransformer("BAAI/bge-large-en-v1.5")
    embeddings_perguntas = modelo.encode(perguntas_bd, convert_to_tensor=True) if perguntas_bd else None
    embeddings_respostas = modelo.encode(respostas_bd, convert_to_tensor=True) if respostas_bd else None

    with open(caminho_json, "r", encoding="utf-8") as f:
        dados = json.load(f)

    for entrada in dados:
        pergunta_raw = entrada.get("pergunta") or entrada.get("Pergunta", "")
        pergunta = limpar_texto(pergunta_raw)
        respostas = entrada.get("respostas") or entrada.get("Respostas", [])

        if not pergunta:
            continue

        ident_pergunta = extrair_ident_pergunta(pergunta_raw, entrada)
        if not ident_pergunta:
            print(f"⚠️ Sem identificador-pergunta (tipo DPQ.010) para: {pergunta_raw[:80]!r}. A ignorar.")
            continue

        # já existe exatamente igual? (evita duplicado literal)
        if pergunta in perguntas_bd:
            print(f"⚠️ Pergunta duplicada ignorada (exata): '{pergunta}'")
            continue

        # decidir identificador-semantico da pergunta
        sem_id_pergunta, proximo_sem_pergunta, embeddings_perguntas = atribuir_identificador(
            pergunta, perguntas_bd, perguntas_sem_ids,
            modelo, embeddings_perguntas, proximo_sem_pergunta
        )

        # inserir pergunta
        cursor.execute(
            "INSERT INTO perguntas (texto, `identificador-pergunta`, `identificador-semantico`) VALUES (%s, %s, %s)",
            (pergunta_raw.strip(), ident_pergunta, sem_id_pergunta)
        )
        pergunta_id = cursor.lastrowid
        print(f"✅ Pergunta: '{pergunta}' id={pergunta_id} ident-pergunta={ident_pergunta} sem={sem_id_pergunta}")

        # atualizar memória local para próximas comparações
        perguntas_bd.append(pergunta)
        perguntas_sem_ids.append(sem_id_pergunta)

        # ---- respostas (herdam mesmo identificador-pergunta) ----
        for resp in respostas:
            texto_resp_raw = resp.get("texto") or resp.get("opção", "")
            texto_resp = limpar_texto(texto_resp_raw.strip())
            if not texto_resp:
                continue

            # decidir identificador-semantico da resposta
            sem_id_resp = None
            if respostas_bd:
                nova_emb = modelo.encode(texto_resp, convert_to_tensor=True)
                sims = util.cos_sim(nova_emb, embeddings_respostas)
                max_sim = sims.max().item()
                if max_sim >= 0.85:
                    idx = sims.argmax().item()
                    sem_id_resp = respostas_sem_ids[idx]
                    print(f"♻️ Resposta semelhante → sem={sem_id_resp}")
            if sem_id_resp is None:
                sem_id_resp = proximo_sem_resposta
                proximo_sem_resposta += 1
                print(f"🆕 Nova resposta → novo sem={sem_id_resp}")

            cursor.execute(
                "INSERT INTO respostas (texto, `identificador-pergunta`, `identificador-semantico`) VALUES (%s, %s, %s)",
                (texto_resp_raw.strip(), ident_pergunta, sem_id_resp)
            )
            id_resposta = cursor.lastrowid
            print(f"✅ Resposta: '{texto_resp}' id={id_resposta} ident-pergunta={ident_pergunta} sem={sem_id_resp}")

            # atualizar memória local para próximas comparações
            respostas_bd.append(texto_resp)
            respostas_sem_ids.append(sem_id_resp)
            emb_nova = modelo.encode(texto_resp, convert_to_tensor=True).unsqueeze(0).to(torch.float32)
            embeddings_respostas = torch.cat((embeddings_respostas, emb_nova), dim=0) if embeddings_respostas is not None else emb_nova

            # ligação P ↔ R
            cursor.execute(
                "INSERT IGNORE INTO pergunta_resposta (pergunta_id, resposta_id, texto_pergunta, texto_resposta) VALUES (%s, %s, %s, %s)",
                (pergunta_id, id_resposta, pergunta_raw.strip(), texto_resp_raw.strip())
            )

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Done: pergunta/respostas com o mesmo `identificador-pergunta` e agrupamento por `identificador-semantico`.")
