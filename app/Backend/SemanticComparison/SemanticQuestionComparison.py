import os
import json
import re
import mysql.connector
import requests
import torch
from sentence_transformers import SentenceTransformer, util


# ⚙️ Conexão à base de dados
def conectar_bd():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3307)),
        user=os.getenv("DB_USER", "user"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "projetofinal_ins")
    )

# 🔠 Limpeza
def limpar_texto(p):
    p = re.sub(r"[^\x00-\x7F]+", " ", p)
    p = re.sub(r"(?i)go to.*", "", p)
    return p.strip()

# 🤖 Prompt para LLM
def construir_prompt_binario(p1, p2):
    return f"""
O teu objetivo é avaliar se duas perguntas significam essencialmente a mesma coisa.

✅ Diz "SIM" se forem semanticamente equivalentes.
❌ Diz "NÃO" se forem diferentes.

❓ Pergunta 1: "{p1}"
❓ Pergunta 2: "{p2}"
"""

# LLM via API do Ollama
def perguntar_ao_llm(p1, p2, modelo="mistral", url="http://ollama:11434/api/chat"):
    prompt = construir_prompt_binario(p1, p2)

    payload = {
        "model": modelo,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        resposta_total = ""
        response = requests.post(url, json=payload, stream=True, timeout=90)

        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            resposta_total += data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
            return resposta_total.strip().lower()
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            return None
    except Exception as e:
        print("❌ Erro ao contactar o LLM:", e)
        return None

# ✅ Nova função reutilizável para atribuir identificador
def atribuir_identificador(pergunta, perguntas_bd, identificadores_bd, modelo, embeddings_bd, proximo_id):
    pergunta_limpa = limpar_texto(pergunta)

    if not perguntas_bd:
        return proximo_id, proximo_id + 1, modelo.encode([pergunta_limpa], convert_to_tensor=True)

    emb_nova = modelo.encode(pergunta_limpa, convert_to_tensor=True)
    similaridades = util.cos_sim(emb_nova, embeddings_bd)[0]
    score_max = float(similaridades.max())
    idx = int(similaridades.argmax())
    pergunta_bd = perguntas_bd[idx]
    print(f"\n🔍 Comparação:")
    print(f"🆕 Nova pergunta: {pergunta}")
    print(f"📁 Mais semelhante: {pergunta_bd}")
    print(f"📊 Similaridade: {score_max:.2f}%\n")

    if score_max >= 0.80:
        return identificadores_bd[idx], proximo_id, torch.vstack([embeddings_bd, emb_nova])
    elif score_max < 0.70:
        return proximo_id, proximo_id + 1, torch.vstack([embeddings_bd, emb_nova])
    else:
        resposta = perguntar_ao_llm(pergunta, pergunta_bd)
        if resposta and "sim" in resposta:
            print(f"Resposta do LLM: {resposta}")
            return identificadores_bd[idx], proximo_id, torch.vstack([embeddings_bd, emb_nova])
        else:
            return proximo_id, proximo_id + 1, torch.vstack([embeddings_bd, emb_nova])




if __name__ == "__main__":
    atribuir_identificador()
