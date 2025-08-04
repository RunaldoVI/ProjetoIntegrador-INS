# AnaliseTerminal.py

import sys
import os

# Adiciona as subpastas com acentos ao sys.path
base_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(base_dir, "Backend", "Extração"))
sys.path.append(os.path.join(base_dir, "Backend", "Limpeza"))

# Importações de funções
from TextExtractorPDF import extrair_texto_para_txt
from VisualExtractorPDF import extrair_blocos_visuais
from PreProcessamento import (
    identificar_secao_mais_comum,
    extrair_blocos_limpos,
    separar_pergunta_respostas
)

if len(sys.argv) < 2:
    print("❌ Uso: python AnaliseTerminal.py caminho_para_pdf")
    sys.exit(1)

caminho_pdf = sys.argv[1]

# Extrair texto com pdfplumber
caminho_txt = extrair_texto_para_txt(caminho_pdf)
print(f"\n📝 Texto extraído para: {caminho_txt}")

# Extrair texto visual com PyMuPDF (fitz) — texto apenas, sem coordenadas
_ = extrair_blocos_visuais(caminho_pdf)
print("📐 Blocos visuais extraídos (sem coordenadas)")

# Ler conteúdo do .txt
with open(caminho_txt, encoding="utf-8") as f:
    conteudo = f.read()

# Dividir em páginas
paginas = conteudo.split("===== Página ")
paginas_texto = [p.split("\n", 1)[1] if "\n" in p else p for p in paginas if p.strip()]

# Identificar secção comum
secao_geral = identificar_secao_mais_comum(paginas_texto)

# Processar blocos de cada página
for i, pagina in enumerate(paginas_texto, start=1):
    blocos = extrair_blocos_limpos(pagina)
    print(f"\n📄 Página {i} - {len(blocos)} blocos encontrados")

    for bloco in blocos:
        resultado = separar_pergunta_respostas(bloco, secao_geral)
        if resultado:
            print(f"\n🆔 {resultado['Identificador']}")
            print(f"📚 Secção: {resultado['Secção']}")
            print(f"❓ Pergunta: {resultado['Pergunta']}")
            print("🔘 Respostas:")
            for r in resultado['Respostas']:
                print(f"  - {r['opção']} ({r['valor']})")
        else:
            print("\n⚠️ Bloco ignorado (sem respostas válidas)")
