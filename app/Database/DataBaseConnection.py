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

def importar_json_para_bd(caminho_json):
    conn = conectar_bd()
    cursor = conn.cursor()

    # Perguntas
    cursor.execute("SELECT texto, identificador FROM perguntas")
    dados_bd = cursor.fetchall()
    perguntas_bd = [limpar_texto(p[0]) for p in dados_bd]
    identificadores_bd = [p[1] for p in dados_bd]

    cursor.execute("SELECT MAX(identificador) FROM perguntas")
    res = cursor.fetchone()
    proximo_id = res[0] + 1 if res and res[0] is not None else 1

    # Respostas
    cursor.execute("SELECT texto, identificador FROM respostas")
    respostas_raw = cursor.fetchall()
    respostas_bd = [limpar_texto(r[0]) for r in respostas_raw]
    respostas_identificadores = [r[1] for r in respostas_raw]

    cursor.execute("SELECT MAX(identificador) FROM respostas")
    res = cursor.fetchone()
    proximo_id_resposta = res[0] + 1 if res and res[0] is not None else 1

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

        if pergunta in perguntas_bd:
            print(f"⚠️ Pergunta duplicada ignorada (exata): '{pergunta}'")
            continue

        identificador, proximo_id, embeddings_perguntas = atribuir_identificador(
            pergunta, perguntas_bd, identificadores_bd,
            modelo, embeddings_perguntas, proximo_id
        )

        cursor.execute("INSERT INTO perguntas (texto, identificador) VALUES (%s, %s)", (pergunta_raw.strip(), identificador))
        pergunta_id = cursor.lastrowid
        print(f"✅ Inserida pergunta: '{pergunta}' com ID {pergunta_id} (identificador {identificador})")

        perguntas_bd.append(pergunta)
        identificadores_bd.append(identificador)

        for resp in respostas:
            texto_resp_raw = resp.get("texto") or resp.get("opção", "")
            texto_resp = limpar_texto(texto_resp_raw.strip())
            if not texto_resp:
                continue

            identificador_resp = None

            if respostas_bd:
                nova_emb = modelo.encode(texto_resp, convert_to_tensor=True)
                similaridades = util.cos_sim(nova_emb, embeddings_respostas)
                max_sim = similaridades.max().item()
                if max_sim >= 0.85:
                    idx = similaridades.argmax().item()
                    identificador_resp = respostas_identificadores[idx]
                    print(f"♻️ Resposta '{texto_resp}' semelhante. Reutilizado identificador {identificador_resp}")

            if identificador_resp is None:
                identificador_resp = proximo_id_resposta
                proximo_id_resposta += 1
                print(f"🆕 Nova resposta. Atribuído identificador {identificador_resp}")

            # Inserir sempre (pode ter texto diferente mas mesmo identificador)
            cursor.execute("INSERT INTO respostas (texto, identificador) VALUES (%s, %s)", (texto_resp_raw.strip(), identificador_resp))
            id_resposta = cursor.lastrowid

            # Atualizar memória local
            respostas_bd.append(texto_resp)
            respostas_identificadores.append(identificador_resp)
            emb_nova = modelo.encode(texto_resp, convert_to_tensor=True).unsqueeze(0).to(torch.float32)
            embeddings_respostas = torch.cat((embeddings_respostas, emb_nova), dim=0) if embeddings_respostas is not None else emb_nova

            print(f"✅ Resposta inserida: '{texto_resp}' com ID {id_resposta} (identificador {identificador_resp})")

            # Verificar se já existe ligação
            cursor.execute(
                "SELECT COUNT(*) FROM pergunta_resposta WHERE pergunta_id = %s AND resposta_id = %s",
                (pergunta_id, id_resposta)
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO pergunta_resposta (pergunta_id, resposta_id, texto_pergunta, texto_resposta) VALUES (%s, %s, %s, %s)",
                    (pergunta_id, id_resposta, pergunta_raw.strip(), texto_resp_raw.strip())
                )
                print(f"🔗 Ligação criada: pergunta {pergunta_id} ⇨ resposta {id_resposta}")
            else:
                print(f"⚠️ Ligação já existia: pergunta {pergunta_id} ⇨ resposta {id_resposta}")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Inserção concluída com verificação semântica de perguntas e respostas.")
