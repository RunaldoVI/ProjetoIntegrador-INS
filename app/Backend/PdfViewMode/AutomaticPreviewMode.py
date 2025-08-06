import sys
import os
import json
import re

print("=== AutomaticPreviewMode.py carregado: versão final com limpeza de ruído ===")

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

def preparar_texto_para_llm(raw: str) -> str:
    linhas = raw.splitlines()
    padroes_remover = [
        r"^\s*HAND CARD", r"^\s*CAPI INSTRUCTION", r"^\s*SOFT EDIT",
        r"^\s*HARD EDIT", r"^\s*INTERVIEWER INSTRUCTION", r"^\s*CHECK ITEM",
        r"^\s*BOX", r"^\s*ENTER #", r"^\s*DISPLAY QUANTITY", r"^\s*DISPLAY NUMBER",
        r"^\s*ALQ-\d+", r".*PREVIOUSLY REPORTED.*", r".*CODED\s+‘?0’?.*",
        r"^\s*IF SP .*", r"^\s*ERROR MESSAGE.*", r"^\s*RANGE .*", r"^\s*YES IF .*",
        r"^\s*SOFT CHECK.*", r"^\s*\|___\|___\|___\|", r"^\s*--+$"
    ]
    linhas_filtradas = []
    for linha in linhas:
        if any(re.search(pat, linha, flags=re.IGNORECASE) for pat in padroes_remover):
            continue
        if re.fullmatch(r"\s*\d+\s*", linha):
            continue
        linhas_filtradas.append(linha.strip())

    texto = "\n".join(linhas_filtradas)
    texto = re.sub(r"^\s*\[.*?\]\s*", "", texto)
    return texto

def bloco_valido(texto: str) -> bool:
    """Ignora blocos com 1-2 linhas sem interrogação (provável ruído técnico)."""
    if len(texto.splitlines()) <= 2 and not re.search(r"\?\s*$", texto, re.MULTILINE):
        return False
    return True

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
    if bloco["tipo"] != "Pergunta" or len(bloco["texto"].strip()) < 10:
        continue

    texto_original = bloco["texto"]
    texto = preparar_texto_para_llm(texto_original)

    if not bloco_valido(texto):
        print(f"⚠️ Bloco {j} ignorado (conteúdo de navegação) na página 1")
        continue

    print(f"[DEBUG] Página 1, Bloco {j} - texto a enviar ao LLM:")
    print(texto)
    print("-" * 40)

    estrutura, resposta_final = processar_bloco(texto, pergunta, secao_geral, preview_pergunta)
    if not resposta_final:
        print(f"⚠️ Bloco {j} rejeitado ou inválido (página 1)")
        guardar_rejeitado(1, j, bloco)
        continue

    ident = resposta_final["Identificador"].strip()
    if ident in identificadores_vistos:
        print(f"⚠️ Bloco {j} ignorado (duplicado: {ident})")
        continue

    identificadores_vistos.add(ident)
    blocos_finais.append(resposta_final)

# Demais páginas
for i, texto_pagina in enumerate(restantes_paginas, start=2):
    blocos = extrair_blocos_limpos(texto_pagina)
    if not blocos:
        print(f"\n📄 Página {i} ignorada (sem blocos válidos).")
        continue

    for j, bloco in enumerate(blocos, start=1):
        if bloco["tipo"] != "Pergunta" or len(bloco["texto"].strip()) < 10:
            continue

        texto_original = bloco["texto"]
        texto = preparar_texto_para_llm(texto_original)

        if not bloco_valido(texto):
            print(f"⚠️ Bloco {j} ignorado (conteúdo de navegação) na página {i}")
            continue

        print(f"\n🧠 Página {i}, Bloco {j} - texto a enviar ao LLM:")
        print(texto)
        print("-" * 40)

        estrutura, resposta_final = processar_bloco(texto, pergunta, secao_geral, preview_pergunta)
        if not resposta_final:
            print(f"⚠️ Bloco {j} rejeitado ou inválido (página {i})")
            guardar_rejeitado(i, j, bloco)
            continue

        ident = resposta_final["Identificador"].strip()
        if ident in identificadores_vistos:
            print(f"⚠️ Bloco {j} ignorado (duplicado: {ident})")
            continue

        identificadores_vistos.add(ident)
        blocos_finais.append(resposta_final)

output_path = os.path.join(os.getcwd(), "output_blocos_conciliados.json")
print(f"\n[DEBUG] Gravando {len(blocos_finais)} blocos em: {output_path}")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(blocos_finais, f, indent=2, ensure_ascii=False)
print("📁 Output final guardado.")

importar_json_para_bd("output_blocos_conciliados.json")
executar()
