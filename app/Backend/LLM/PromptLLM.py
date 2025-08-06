import requests
import json

def obter_pergunta(instrucoes_adicionais=None):
    prompt = (
        "Tens à tua frente um excerto de um questionário estruturado (como o NHANES). "
        "Extrai, de forma organizada, todas as perguntas válidas com base nas instruções abaixo.\n\n"

        "❗ Instruções importantes:\n"
        "- Não traduzas nada.\n"
        "- Cada pergunta começa com um identificador único no formato 'XXX.###' (ex: 'DPQ.010', 'DUQ.200', 'ALQ.111', etc).\n"
        "- Se houver um texto introdutório que se aplica a várias perguntas consecutivas (ex: 'Over the last 2 weeks...'), considera esse texto como uma 'Secção' e aplica-o a todas as perguntas seguintes até que o contexto mude.\n"
        "- Se o bloco não tiver secção aplicável, define \"Secção\": \"Nenhuma\".\n"
        "- Ignora qualquer bloco que seja:\n"
        "  - apenas instruções técnicas (ex: 'CHECK ITEM', 'BOX 1', 'GO TO', 'HANDCARD', 'ENTER AGE', etc.),\n"
        "  - ou uma pergunta que não tenha pelo menos uma opção de resposta com valor numérico (ex: 0, 1, 2, ...).\n"
        "- A pergunta pode vir imediatamente após o identificador ou numa linha seguinte. Junta as partes corretamente.\n"
        "- As respostas devem ser listadas com o seu texto e valor numérico.\n\n"

        "✅ Formato obrigatório de saída (em JSON):\n\n"
        "{\n"
        "  \"Identificador\": \"XXX.###\",\n"
        "  \"Secção\": \"Texto da secção ou 'Nenhuma'\",\n"
        "  \"Pergunta\": \"Texto da pergunta\",\n"
        "  \"Respostas\": [\n"
        "    { \"opção\": \"Texto da resposta\", \"valor\": \"0\" },\n"
        "    { \"opção\": \"Texto da resposta\", \"valor\": \"1\" },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Repete este formato JSON para cada pergunta válida."
    )

    if instrucoes_adicionais:
        prompt += "\n\n📌 Instruções adicionais do utilizador:\n" + instrucoes_adicionais.strip()

    return prompt


def enviar_pagina_para_llm(texto_pagina, prompt, modelo="mistral", url="http://localhost:11434/api/chat"):
    """
    Envia um texto para o modelo LLM via Ollama (ou servidor compatível).
    """
    payload = {
        "model": modelo,
        "messages": [
            {
                "role": "system",
                "content": "Estás a interpretar uma página de um questionário clínico estruturado. Responde apenas com base nesta página. Responde sempre no formato JSON definido."
            },
            {
                "role": "user",
                "content": f"{texto_pagina}\n\n{prompt}"
            }
        ]
    }

    resposta_total = ""
    try:
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

    except Exception as e:
        resposta_total = f"❌ Erro de conexão: {e}"

    return resposta_total
