# utils_extracao.py
import json
import re
from LLM.PromptLLM import enviar_pagina_para_llm
from Limpeza.PreProcessamento import separar_pergunta_respostas

def processar_bloco(bloco, pergunta, secao_geral, preview_identificador=None):
    if len(bloco.strip()) < 20:
        return None, None

    estrutura = separar_pergunta_respostas(bloco, secao_geral)
    if estrutura is None:
        print("❌ Pré-processamento falhou.")
        return None, None

    if estrutura.get("Identificador", "").strip() == preview_identificador:
        print(f"⏭️  Ignorado (mesmo identificador do preview: {preview_identificador})")
        return None, None

    # ✅ Usa sempre o LLM
    resposta_llm_raw = enviar_pagina_para_llm(bloco, pergunta)

    try:
        match = re.search(r"\{.*\}", resposta_llm_raw, re.DOTALL)
        resposta_llm = json.loads(match.group(0)) if match else {}
    except:
        resposta_llm = {}

    if (
        isinstance(resposta_llm, dict)
        and resposta_llm.get("Pergunta")
        and resposta_llm.get("Respostas")
    ):
        print("🤖 A usar resposta do LLM (válida)")
        return estrutura, resposta_llm

    print("⚠️ LLM respondeu mal ou incompleto. Ignorado.")
    return None, None
