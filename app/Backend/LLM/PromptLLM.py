import requests
import json
import os
import time

def obter_pergunta(instrucoes_adicionais=None):
    base = (
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
    if instrucoes_adicionais:
        base += "\n\n📌 Instruções adicionais do utilizador:\n" + instrucoes_adicionais.strip()
    return base



def enviar_pagina_para_llm(texto_pagina, pergunta, modelo="mistral", url="http://ollama:11434/api/chat"):
    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Estás a interpretar uma página de um questionário clínico. Responde apenas com base nesta página."},
            {"role": "user", "content": f"{texto_pagina}\n\n{pergunta}"}
        ]
    }

    resposta_total = ""
    response = requests.post(url, json=payload, stream=True)

    if response.status_code == 200:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        resposta_total += data["message"]["content"]
                except json.JSONDecodeError:
                    resposta_total += f"\n⚠️ Erro a processar linha: {line}"
    else:
        resposta_total = f"❌ Erro: {response.status_code}\n{response.text}"

    return resposta_total