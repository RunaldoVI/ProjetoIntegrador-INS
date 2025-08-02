import sys
import json
import re
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))

from Extração.TextExtractorPDF import extrair_texto_para_txt
from LLM.PromptLLM import enviar_pagina_para_llm, obter_pergunta
from Extração.VisualExtractorPDF import extrair_blocos_visuais
from Limpeza.PreProcessamento import (
    identificar_secao_mais_comum,
    extrair_blocos_limpos,
    separar_pergunta_respostas,
    limpar_estrutura_json,
    conciliar_estrutura
)
from DataBaseConnection import importar_json_para_bd


if len(sys.argv) < 2:
    print("❌ Uso: python modo_preview.py caminho_para_pdf")
    sys.exit(1)

caminho_pdf = sys.argv[1]
caminho_txt = extrair_texto_para_txt(caminho_pdf)
extrair_blocos_visuais(caminho_pdf)

with open(caminho_txt, "r", encoding="utf-8") as f:
    conteudo = f.read()

paginas = [p.strip() for p in conteudo.split("===== Página") if p.strip()]
secao_geral = identificar_secao_mais_comum(paginas)
pergunta = obter_pergunta()

if not paginas:
    print("❌ Nenhuma página encontrada no PDF.")
    sys.exit(0)

texto_pagina = paginas[0]
blocos = extrair_blocos_limpos(texto_pagina)

if not blocos:
    print("❌ Primeira página não tem blocos válidos.")
    sys.exit(0)

for j, bloco in enumerate(blocos, start=1):
    if len(bloco) < 20:
        continue

    estrutura = separar_pergunta_respostas(bloco, secao_geral)
    print(f"\n🧠 Pré-visualização - Bloco {j}:")
    print(json.dumps(estrutura, indent=2, ensure_ascii=False))

    resposta_llm = enviar_pagina_para_llm(bloco, pergunta)

    try:
        match = re.search(r"\{.*\}", resposta_llm, re.DOTALL)
        resposta_llm = json.loads(match.group(0)) if match else {}
    except:
        resposta_llm = {}

    resposta_final = conciliar_estrutura(estrutura, limpar_estrutura_json(resposta_llm))

    print(f"\n🧠 Resposta do LLM:")
    print(json.dumps(resposta_final, indent=2, ensure_ascii=False))

    with open("preview_output.json", "w", encoding="utf-8") as f:
        json.dump(resposta_final, f, indent=2, ensure_ascii=False)

    print(json.dumps({"status": "preview", "mensagem": "Pré-visualização concluída."}))
    break  # apenas o primeiro bloco