import requests
import json
import os

CHAT_MODEL = os.getenv("CHAT_MODEL", "mistral")

# --- Contador de tokens simples ---
def contar_tokens_simples(texto):
    palavras = texto.strip().split()
    tokens_estimados = int(len(palavras) / 0.75)
    return tokens_estimados


# --- Prompt base para análise ---
def obter_pergunta(instrucoes_adicionais=None):
    prompt = (
        "Tens à tua frente um excerto de um questionário estruturado (como o NHANES). "
        "Extrai, de forma organizada, todas as perguntas válidas com base nas instruções abaixo.\n\n"
        "❗ Instruções importantes:\n"
        "- Não traduzas nada.\n"
        "- Cada pergunta começa com um identificador único no formato 'XXX.###'.\n"
        "- Se houver um texto introdutório que se aplica a várias perguntas consecutivas considera esse texto como uma 'Secção' e aplica-o a todas as perguntas seguintes até que o contexto mude.\n"
        "- Se o bloco não tiver secção aplicável, define \"Secção\": \"Nenhuma\".\n"
        "- Ignora qualquer bloco que seja:\n"
        "  - apenas instruções técnicas (ex: 'CHECK ITEM', 'BOX 1', 'GO TO', 'HANDCARD', 'ENTER AGE', etc.),\n"
        "  - ou uma pergunta que não tenha pelo menos uma opção de resposta com valor numérico (ex: 0, 1, 2, ...).\n"
        "- A pergunta pode vir imediatamente após o identificador ou numa linha seguinte. Junta as partes corretamente.\n"
        "- As respostas devem ser listadas com o seu texto e valor numérico.\n\n"
        "- Matem as respostas todas e a estrutura original do ficheiro."
        "✅ Formato obrigatório de saída (em JSON):\n\n"
        "{\n"
        "  \"Identificador\": \"XXX.###\",\n"
        "  \"Secção\": \"Texto da secção ou 'Nenhuma'\",\n"
        "  \"Pergunta\": \"Texto da pergunta\",\n"
        "  \"Respostas\": [\n"
        "    { \"opção\": \"Texto da resposta\", \"valor\": \"0\" },\n"
        "    { \"opção\": \"Texto da resposta\", \"valor\": \"1\" },\n"
        "    etc..\n"
        "  ]\n"
        "}\n\n"
        "Returna me o output em formato JSON!"
    )

    if instrucoes_adicionais:
        prompt += (
            "\n\n📌 Instruções adicionais do utilizador:\n"
            f"{instrucoes_adicionais.strip()}\n"
        )

    return prompt


# --- Envio para o modelo via Ollama ---
def enviar_pagina_para_llm(texto_pagina, prompt, modelo=CHAT_MODEL, url="http://ollama:11434/api/chat", debug=False):
    conteudo_user = f"{texto_pagina}\n\n{prompt}"
    tokens_estimados = contar_tokens_simples(conteudo_user)

    print("\n📤 Enviando para o LLM...")
    print(f"🔹 Modelo: {modelo}")
    print(f"🔢 Tokens estimados: {tokens_estimados}")
    print(f"📄 Página (preview): {texto_pagina[:150].replace(chr(10), ' ')}...")
    print(f"📝 Prompt (preview): {prompt[:150].replace(chr(10), ' ')}...\n")

    if debug:
        print("--- TEXTO COMPLETO ENVIADO ---")
        print(conteudo_user)
        print("--- FIM ---\n")

    payload = {
        "model": modelo,
        "messages": [
            {
                "role": "system",
                "content": "Estás a interpretar uma página de um questionário clínico estruturado. Responde apenas com base nesta página. Responde sempre no formato JSON definido."
            },
            {
                "role": "user",
                "content": conteudo_user
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
            resposta_total = f"❌ Erro HTTP {response.status_code}:\n{response.text}"

    except Exception as e:
        resposta_total = f"❌ Erro de conexão: {e}"

    print("\n🧠 Resposta completa do LLM:\n")
    print(resposta_total.strip())
    print("\n✅ Fim da resposta.\n")
    return resposta_total
