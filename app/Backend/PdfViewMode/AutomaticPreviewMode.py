import sys
import os
import json
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Database")))
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
from DataBaseConnection import importar_json_para_bd

if len(sys.argv) < 2:
    print("❌ Uso: python modo_automatico.py caminho_para_pdf")
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

preview_path = "preview_output.json"
preview_pergunta = None

# 🔁 Reaproveitar preview se existir
if os.path.exists(preview_path):
    with open(preview_path, "r", encoding="utf-8") as f:
        bloco_preview = json.load(f)
        blocos_finais.append(bloco_preview)
        preview_pergunta = bloco_preview.get("Pergunta", "").strip()
    print("✅ Preview carregado e reaproveitado.")
else:
    print("⚠️ Nenhum preview encontrado.")

# 🟨 Processar o resto da primeira página (exceto o preview)
primeira_pagina = paginas[0]
restantes_paginas = paginas[1:]

blocos = extrair_blocos_limpos(primeira_pagina)
for j, bloco in enumerate(blocos, start=1):
    if len(bloco) < 20:
        continue

    estrutura = separar_pergunta_respostas(bloco, secao_geral)
    if estrutura is None:
        continue

    if estrutura.get("Identificador") == bloco_preview.get("Identificador"):
        print(f"⏭️  Bloco {j} ignorado (mesmo identificador do preview: {estrutura.get('Identificador')})")
        continue

    print(f"\n🧠 Página 1, Bloco {j} (após preview):")
    print(json.dumps(estrutura, indent=2, ensure_ascii=False))
    print("-" * 50)

    resposta_llm = enviar_pagina_para_llm(bloco, pergunta)
    print("🔄 Resposta original do LLM:")
    print(resposta_llm)
    try:
        match = re.search(r"\{.*\}", resposta_llm, re.DOTALL)
        resposta_llm = json.loads(match.group(0)) if match else {}
    except:
        resposta_llm = {}

    resposta_limpa = limpar_estrutura_json(resposta_llm)
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

# 📄 Agora continua normalmente com as restantes páginas
for i, texto_pagina in enumerate(restantes_paginas, start=2):
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

        print(f"\n🧠 Página {i}, Bloco {j}:")
        print(json.dumps(estrutura, indent=2, ensure_ascii=False))
        print("-" * 50)

        resposta_llm = enviar_pagina_para_llm(bloco, pergunta)

        try:
            match = re.search(r"\{.*\}", resposta_llm, re.DOTALL)
            resposta_llm = json.loads(match.group(0)) if match else {}
        except:
            resposta_llm = {}

        resposta_limpa = limpar_estrutura_json(resposta_llm)
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

with open("output_blocos_conciliados.json", "w", encoding="utf-8") as f:
    json.dump(blocos_finais, f, indent=2, ensure_ascii=False)
print("\n📁 Output final guardado em 'output_blocos_conciliados.json'")

importar_json_para_bd("output_blocos_conciliados.json")
executar()