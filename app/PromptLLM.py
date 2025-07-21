import requests
import json
import os
import time

def obter_pergunta():
    return (
        "Consegues fazer uma lista organizada com os identificadores, as perguntas e as suas opções de resposta "
        "que aparecem neste questionário?\n\n"
        "❗ Instruções importantes:\n"
        "- Não traduzas nada.\n"
        "- Se houver algum texto introdutório ou enunciado que se aplica a várias perguntas seguidas (por exemplo, uma frase geral antes de uma lista de perguntas), considera esse texto como uma **Secção** comum.\n"
        "- Se não houver um enunciado comum, coloca 'Secção: Nenhuma'.\n"
        "- **Ignora blocos que sejam apenas instruções, anotações ou encaminhamentos** (ex: 'BOX 2', 'GO TO', 'CHECK ITEM', etc).\n"
        "- **Ignora qualquer pergunta que não tenha pelo menos uma opção de resposta com valor numérico associado** (ex: '(0)', '(1)', '(2)'...).\n"
        "- Usa exatamente o seguinte formato:\n\n"
        "Identificador: [código]\n"
        "Secção: [texto da secção ou 'Nenhuma']\n"
        "Pergunta: [texto completo da pergunta]\n"
        "Respostas:\n"
        "  - [opção 1] (valor)\n"
        "  - [opção 2] (valor)\n"
        "  - ...\n\n"
        "Consegues colocar tudo num formato JSON estruturado?\n"
    )

def enviar_pagina_para_llm(texto_pagina, pergunta, tentativas=10):
    url = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
    modelo = os.getenv("OLLAMA_MODEL", "mistral")

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Estás a interpretar uma página de um questionário clínico. Responde apenas com base nesta página."},
            {"role": "user", "content": f"{texto_pagina}\n\n{pergunta}"}
        ]
    }

    for tentativa in range(1, tentativas + 1):
        try:
            response = requests.post(url, json=payload, stream=True, timeout=30)
            if response.status_code == 200:
                resposta_total = ""
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                resposta_total += data["message"]["content"]
                        except json.JSONDecodeError:
                            resposta_total += f"\n⚠️ Erro a processar linha: {line}"
                return resposta_total
            else:
                return f"❌ Erro: {response.status_code}\n{response.text}"

        except requests.exceptions.RequestException as e:
            print(f"⏳ [Tentativa {tentativa}/{tentativas}] Ollama não disponível ainda. A aguardar 5s...")
            time.sleep(5)

    return "❌ Erro: Falha ao conectar ao Ollama após várias tentativas."