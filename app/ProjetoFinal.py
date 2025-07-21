from TextExtractorPDF import extrair_texto_para_txt
from PromptLLM import enviar_pagina_para_llm, obter_pergunta

# Caminho para o PDF
caminho_pdf = "../documents/DPQ_J.pdf"

# 1. Extrair texto do PDF
caminho_txt = extrair_texto_para_txt(caminho_pdf)
print(f"✅ Texto extraído para {caminho_txt}")

# 2. Ler o conteúdo extraído
with open(caminho_txt, "r", encoding="utf-8") as f:
    conteudo = f.read()

# 3. Separar por páginas
paginas = [p.strip() for p in conteudo.split("===== Página") if p.strip()]

# 4. Obter a pergunta comum
pergunta = obter_pergunta()

# 5. Enviar cada página para a LLM
for i, texto_pagina in enumerate(paginas, start=1):
    if len(texto_pagina) < 20:
        print(f"\n📄 Página {i} ignorada (sem conteúdo significativo).")
        continue

    print(f"\n🧠 Página {i}:")
    resposta = enviar_pagina_para_llm(texto_pagina, pergunta)
    print(resposta)
    print("-" * 50)
