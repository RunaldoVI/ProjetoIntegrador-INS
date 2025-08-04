import mysql.connector
import json
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Backend', 'SemanticComparison')))
from SemanticQuestionComparison import limpar_texto, atribuir_identificador
from sentence_transformers import SentenceTransformer

# 1. Ligação à base de dados
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

    # Carregar perguntas existentes
    cursor.execute("SELECT texto, identificador FROM perguntas")
    dados_bd = cursor.fetchall()
    perguntas_bd = [limpar_texto(p[0]) for p in dados_bd]
    identificadores_bd = [p[1] for p in dados_bd]

    # Próximo identificador
    cursor.execute("SELECT MAX(identificador) FROM perguntas")
    res = cursor.fetchone()
    proximo_id = res[0] + 1 if res and res[0] is not None else 1

    modelo = SentenceTransformer("BAAI/bge-large-en-v1.5")
    embeddings_bd = modelo.encode(perguntas_bd, convert_to_tensor=True) if perguntas_bd else None

    with open(caminho_json, "r", encoding="utf-8") as f:
        dados = json.load(f)

    for entrada in dados:
        pergunta = limpar_texto(entrada.get("pergunta") or entrada.get("Pergunta", ""))
        respostas = entrada.get("respostas") or entrada.get("Respostas", [])

        if not pergunta:
            continue

        identificador, proximo_id, embeddings_bd = atribuir_identificador(
            pergunta, perguntas_bd, identificadores_bd,
            modelo, embeddings_bd, proximo_id
        )

        print(f"✅ Inserida pergunta: '{pergunta}' com identificador {identificador}")
        cursor.execute("INSERT INTO perguntas (texto, identificador) VALUES (%s, %s)", (pergunta, identificador))

        for resp in respostas:
            texto_resp = resp.get("texto") or resp.get("opção")
            if texto_resp:
                cursor.execute("INSERT INTO respostas (texto, identificador) VALUES (%s, %s)", (texto_resp.strip(), identificador))

        perguntas_bd.append(pergunta)
        identificadores_bd.append(identificador)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Inserção com comparação semântica feita com sucesso.")
