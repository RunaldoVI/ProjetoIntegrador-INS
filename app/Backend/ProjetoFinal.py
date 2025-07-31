import os
import sys
import requests
import json
import pdfplumber
import subprocess
import re

from Extração.TextExtractorPDF import extrair_texto_para_txt
from LLM.PromptLLM import enviar_pagina_para_llm, obter_pergunta
from Extração.VisualExtractorPDF import extrair_blocos_visuais
from ExcelWriter.ExcelWriter import executar
from Limpeza.PreProcessamento import (
    identificar_secao_mais_comum,
    extrair_blocos_limpos,
    separar_pergunta_respostas,
    limpar_estrutura_json,
    motivo_resposta_incompleta,
    conciliar_estrutura
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Database")))
from DataBaseConnection import importar_json_para_bd

### ⬇️ 1. Argumentos
if len(sys.argv) < 3:
    print("❌ Uso: python script.py caminho_para_pdf --modo preview|automatico")
    sys.exit(1)

caminho_pdf = sys.argv[1]
modo = sys.argv[2].lower()

if modo not in ["--modo", "preview", "automatico"]:
    print("❌ Modo inválido. Use '--modo preview' ou '--modo automatico'")
    sys.exit(1)

# === Etapas iniciais
caminho_txt = extrair_texto_para_txt(caminho_pdf)
print(f"\n✅ Texto extraído para {caminho_txt}")

blocos_txt = extrair_blocos_visuais(caminho_pdf)
print(f"✅ Blocos visuais extraídos com fitz para {blocos_txt}")

with open(caminho_txt, "r", encoding="utf-8") as f:
    conteudo = f.read()

paginas = [p.strip() for p in conteudo.split("===== Página") if p.strip()]
secao_geral = identificar_secao_mais_comum(paginas)
pergunta = obter_pergunta()

blocos_finais = []

### 🔍 MODO PREVIEW (só analisa 1ª página e pergunta)
if sys.argv[2] == "preview":
    i = 1
    texto_pagina = paginas[0]
    blocos = extrair_blocos_limpos(texto_pagina)

    if not blocos:
        print("❌ Primeira página não tem blocos válidos.")
        sys.exit(0)

    for j, bloco in enumerate(blocos, start=1):
        if len(bloco) < 20:
            continue

        estrutura = separar_pergunta_respostas(bloco, secao_geral)
        print(f"\n🧠 Pré-visualização - Página {i}, Bloco {j}:")
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
        sys.exit(0)
        break  # apenas primeiro bloco

### 🚀 MODO AUTOMÁTICO (processa tudo como já fazias)
for i, texto_pagina in enumerate(paginas, start=1):
    blocos = extrair_blocos_limpos(texto_pagina)
    if not blocos:
        print(f"\n📄 Página {i} ignorada (sem blocos válidos).")
        continue

    for j, bloco in enumerate(blocos, start=1):
        if len(bloco) < 20:
            continue

        estrutura = separar_pergunta_respostas(bloco, secao_geral)
        if estrutura is None:
            continue

        print(f"\n🧠 Página {i}, Bloco {j} (antes do LLM):")
        print(json.dumps(estrutura, indent=2, ensure_ascii=False))
        print("-" * 50)

        resposta_llm = enviar_pagina_para_llm(bloco, pergunta)

        if isinstance(resposta_llm, str):
            try:
                match = re.search(r"\{.*\}", resposta_llm, re.DOTALL)
                if match:
                    resposta_llm = json.loads(match.group(0))
                else:
                    raise json.JSONDecodeError("JSON não encontrado", resposta_llm, 0)
            except json.JSONDecodeError:
                print(f"⚠️ Erro ao interpretar JSON do LLM no bloco {j} da página {i}")
                resposta_llm = {}

        resposta_limpa = limpar_estrutura_json(resposta_llm)

        if not resposta_limpa or not resposta_limpa.get("Pergunta") or not resposta_limpa.get("Respostas"):
            motivo = motivo_resposta_incompleta(resposta_limpa)
            print(f"⚠️ Bloco {j} da página {i} incompleto → {motivo} → será conciliado com versão original")

        resposta_final = conciliar_estrutura(estrutura, resposta_limpa)

        for k in list(resposta_final.keys()):
            if re.match(r"[A-Z]{2,5}\.\d{3}", k) and isinstance(resposta_final[k], dict):
                resposta_final.update(resposta_final.pop(k))
                resposta_final["Identificador"] = k

        if resposta_final.get("Secção", "Nenhuma") == "Nenhuma":
            resposta_final["Secção"] = estrutura["Secção"]

        if resposta_final.get("Secção") and resposta_final.get("Pergunta", "").startswith(resposta_final["Secção"]):
            resposta_final["Pergunta"] = resposta_final["Pergunta"].replace(resposta_final["Secção"], "").strip(": ").strip()

        blocos_finais.append(resposta_final)

        print(f"\n🧠 Página {i}, Bloco {j} (depois do LLM):")
        print(json.dumps(resposta_final, indent=2, ensure_ascii=False))
        print("=" * 70)

# Exportar JSON final
with open("output_blocos_conciliados.json", "w", encoding="utf-8") as f:
    json.dump(blocos_finais, f, indent=2, ensure_ascii=False)
print("\n📁 Output final guardado em 'output_blocos_conciliados.json'")

# BD + Excel
importar_json_para_bd("output_blocos_conciliados.json")
executar()
