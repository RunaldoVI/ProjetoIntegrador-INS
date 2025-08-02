# utils_extracao.py
import json
import re
from LLM.PromptLLM import enviar_pagina_para_llm
from Limpeza.PreProcessamento import (
    separar_pergunta_respostas,
    limpar_estrutura_json,
    conciliar_estrutura
)

def processar_bloco(bloco, pergunta, secao_geral, preview_identificador=None):
    if len(bloco) < 20:
        return None

    estrutura = separar_pergunta_respostas(bloco, secao_geral)
    if estrutura is None:
        return None

    if estrutura.get("Pergunta", "").strip() == preview_identificador:
        print("⏭️  Ignorado (mesma pergunta do preview)")
        return None

    resposta_llm = enviar_pagina_para_llm(bloco, pergunta)

    try:
        match = re.search(r"\{.*\}", resposta_llm, re.DOTALL)
        resposta_llm = json.loads(match.group(0)) if match else {}
    except:
        resposta_llm = {}

    resposta_limpa = limpar_estrutura_json(resposta_llm)
    resposta_final = conciliar_estrutura(estrutura, resposta_limpa)

    # Correções finais
    for k in list(resposta_final.keys()):
        if re.match(r"[A-Z]{2,5}\.\d{3}", k) and isinstance(resposta_final[k], dict):
            resposta_final.update(resposta_final.pop(k))
            resposta_final["Identificador"] = k

    if resposta_final.get("Secção", "Nenhuma") == "Nenhuma":
        resposta_final["Secção"] = estrutura.get("Secção", "Nenhuma")

    if resposta_final.get("Secção") and resposta_final.get("Pergunta", "").startswith(resposta_final["Secção"]):
        resposta_final["Pergunta"] = resposta_final["Pergunta"].replace(resposta_final["Secção"], "").strip(": ").strip()

    return resposta_final