# extrair_blocos_azuis_txt.py
import fitz
from identificadores import localizar_ids_pagina
from perguntas import extrair_perguntas_de_ids
from respostas import detectar_blocos_leaders, fundir_blocos_sobrepostos_ou_com_poucas_linhas

def extrair_blocos_azuis_para_txt(pdf_path, saida_txt):
    doc = fitz.open(pdf_path)
    todos_textos = []

    for i, pagina in enumerate(doc, start=1):
        # Localizar IDs e blocos de respostas
        ids, _ = localizar_ids_pagina(pagina, ignorar_caixas=True, leftmost_only=True)
        blocos = detectar_blocos_leaders(pagina)
        blocos = fundir_blocos_sobrepostos_ou_com_poucas_linhas(pagina, blocos)

        # Extrair perguntas com bbox_pergunta (as "caixas azuis")
        perguntas = extrair_perguntas_de_ids(pagina, ids, blocos, require_respostas=True)

        for p in perguntas:
            if not p.get("bbox_pergunta"):
                continue
            # Criar um Rect a partir das coordenadas
            x0, y0, x1, y1 = p["bbox_pergunta"]
            rect = fitz.Rect(x0, y0, x1, y1)
            texto = pagina.get_text("text", clip=rect).strip()
            if texto:
                todos_textos.append(f"[Página {i}] {texto}")

    # Guardar no TXT
    with open(saida_txt, "w", encoding="utf-8") as f:
        f.write("\n\n".join(todos_textos))

    print(f"✅ Extraído {len(todos_textos)} blocos azuis para {saida_txt}")

if __name__ == "__main__":
    extrair_blocos_azuis_para_txt("DPQ_J.pdf", "blocos_azuis.txt")
