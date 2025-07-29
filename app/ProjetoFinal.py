import os
import requests
import json
import pdfplumber
import re
from app.Extração.TextExtractorPDF import extrair_texto_para_txt
from app.LLM.PromptLLM import enviar_pagina_para_llm, obter_pergunta
from app.Extração.VisualExtractorPDF import extrair_blocos_visuais
from app.Limpeza.PreProcessamento import (
    identificar_secao_mais_comum,
    extrair_blocos_limpos,
    separar_pergunta_respostas,
    limpar_estrutura_json,
    motivo_resposta_incompleta,
    conciliar_estrutura
)

<<<<<<< HEAD
=======
# Caminho para o PDF
caminho_pdf = "pdfs-excels/DPQ_J.pdf"
>>>>>>> main


# === Pipeline Principal ===
caminho_pdf = os.path.abspath(os.path.join(os.path.dirname(__file__),"..", "pdfs-excels", "DPQ_J.pdf"))
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

# Salvar JSON com todos os blocos finais
with open("output_blocos_conciliados.json", "w", encoding="utf-8") as f:
    json.dump(blocos_finais, f, indent=2, ensure_ascii=False)
print("\n📁 Output final guardado em 'output_blocos_conciliados.json'")
