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
    separar_pergunta_respostas
)
from DataBaseConnection import importar_json_para_bd
from PdfViewMode.utils_extracao import processar_bloco

def executar_preview(caminho_pdf, instrucoes=""):
    caminho_txt = extrair_texto_para_txt(caminho_pdf)
    extrair_blocos_visuais(caminho_pdf)

    with open(caminho_txt, "r", encoding="utf-8") as f:
        conteudo = f.read()

    paginas = [p.strip() for p in conteudo.split("===== Página") if p.strip()]
    secao_geral = identificar_secao_mais_comum(paginas)
    
    # 🧠 Define a pergunta com instruções personalizadas
    pergunta = obter_pergunta()
    if instrucoes:
        pergunta += f"\n\n📌 Instruções extra do utilizador:\n{instrucoes}"

    if not paginas:
        print("❌ Nenhuma página encontrada no PDF.")
        return

    texto_pagina = paginas[0]
    blocos = extrair_blocos_limpos(texto_pagina)

    if not blocos:
        print("❌ Primeira página não tem blocos válidos.")
        return

    for j, bloco in enumerate(blocos, start=1):
        if bloco["tipo"] != "Pergunta":
            continue
        if len(bloco["texto"].strip()) < 20:
            continue

        print("\n📨 Prompt enviado para o LLM:\n", pergunta)

        estrutura, resposta_final = processar_bloco(bloco["texto"], pergunta, secao_geral)

        if not estrutura or not resposta_final:
            continue

        print(f"\n🧠 Pré-visualização - Bloco {j}:")
        print(json.dumps(estrutura, indent=2, ensure_ascii=False))
        print(f"\n🧠 Resposta do LLM:")
        print(json.dumps(resposta_final, indent=2, ensure_ascii=False))

        with open("preview_output.json", "w", encoding="utf-8") as f:
            json.dump(resposta_final, f, indent=2, ensure_ascii=False)

        print(json.dumps({"status": "preview", "mensagem": "Pré-visualização concluída."}))
        break
        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso: python PreviewMode.py caminho_para_pdf [instrucoes]")
        sys.exit(1)

    caminho_pdf = sys.argv[1]
    instrucoes = sys.argv[2] if len(sys.argv) > 2 else ""
    print("🧪 Instruções recebidas via argumento:", instrucoes)
    executar_preview(caminho_pdf, instrucoes)