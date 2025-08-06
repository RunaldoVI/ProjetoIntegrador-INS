import sys
import os
import json
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))

from Extração.TextExtractorPDF import extrair_texto_para_txt
from Extração.VisualExtractorPDF import extrair_blocos_visuais
from LLM.PromptLLM import obter_pergunta
from ExcelWriter.ExcelWriter import executar
from DataBaseConnection import importar_json_para_bd
from PdfViewMode.utils_extracao import processar_bloco
from Limpeza.PreProcessamento import (
    identificar_secao_mais_comum,
    extrair_blocos_limpos,
)

if len(sys.argv) < 2:
    print("❌ Uso: python AutomaticPreviewMode.py caminho_para_pdf")
    sys.exit(1)

caminho_pdf = sys.argv[1]
caminho_txt = extrair_texto_para_txt(caminho_pdf)
extrair_blocos_visuais(caminho_pdf)

with open(caminho_txt, "r", encoding="utf-8") as f:
    conteudo = f.read()

paginas = [p.strip() for p in conteudo.split("===== Página") if p.strip()]
secao_geral = identificar_secao_mais_comum(paginas)
pergunta = obter_pergunta()

blocos_finais = []
identificadores_vistos = set()
preview_path = "preview_output.json"
preview_pergunta = None

if os.path.exists(preview_path):
    with open(preview_path, "r", encoding="utf-8") as f:
        bloco_preview = json.load(f)
        blocos_finais.append(bloco_preview)
        preview_pergunta = bloco_preview.get("Pergunta", "").strip()
        preview_identificador = bloco_preview.get("Identificador", "").strip()
        identificadores_vistos.add(preview_identificador)
    print("✅ Preview carregado e reaproveitado.")
else:
    print("⚠️ Nenhum preview encontrado.")

def guardar_rejeitado(i, j, bloco):
    with open("rejeitados_debug.json", "a", encoding="utf-8") as f:
        json.dump({"pagina": i, "bloco": j, "texto": bloco["texto"]}, f, ensure_ascii=False)
        f.write(",\n")

# Página 1
primeira_pagina = paginas[0]
restantes_paginas = paginas[1:]
blocos = extrair_blocos_limpos(primeira_pagina)

for j, bloco in enumerate(blocos, start=1):
    if bloco["tipo"] != "Pergunta":
        continue
    if len(bloco["texto"].strip()) < 10:
        continue

    estrutura, resposta_final = processar_bloco(bloco["texto"], pergunta, secao_geral, preview_pergunta)
    if not resposta_final:
        print(f"⚠️ Bloco {j} rejeitado ou inválido (página 1).")
        guardar_rejeitado(1, j, bloco)
        continue

    identificador = resposta_final.get("Identificador", "").strip()
    if identificador in identificadores_vistos:
        print(f"⚠️ Bloco {j} ignorado (identificador duplicado: {identificador})")
        continue

    identificadores_vistos.add(identificador)
    blocos_finais.append(resposta_final)

# Demais páginas
for i, texto_pagina in enumerate(restantes_paginas, start=2):
    blocos = extrair_blocos_limpos(texto_pagina)
    if not blocos:
        print(f"\n📄 Página {i} ignorada (sem blocos válidos).")
        continue

    for j, bloco in enumerate(blocos, start=1):
        if bloco["tipo"] != "Pergunta":
            continue
        if len(bloco["texto"].strip()) < 10:
            continue

        print(f"\n🧠 Página {i}, Bloco {j}:")
        estrutura, resposta_final = processar_bloco(bloco["texto"], pergunta, secao_geral, preview_pergunta)
        if not resposta_final:
            print(f"⚠️ Bloco {j} rejeitado ou inválido (página {i}).")
            guardar_rejeitado(i, j, bloco)
            continue

        identificador = resposta_final.get("Identificador", "").strip()
        if identificador in identificadores_vistos:
            print(f"⚠️ Bloco {j} ignorado (identificador duplicado: {identificador})")
            continue

        identificadores_vistos.add(identificador)
        blocos_finais.append(resposta_final)

with open("output_blocos_conciliados.json", "w", encoding="utf-8") as f:
    json.dump(blocos_finais, f, indent=2, ensure_ascii=False)
print("\n📁 Output final guardado em 'output_blocos_conciliados.json'")


importar_json_para_bd("output_blocos_conciliados.json")
executar()




