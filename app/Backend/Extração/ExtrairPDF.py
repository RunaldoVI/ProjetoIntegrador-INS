# ExtrairPDF.py
import os, sys, fitz, cv2, numpy as np
from identificadores import localizar_ids_pagina
from perguntas import extrair_perguntas_de_ids
from respostas import detectar_blocos_leaders, fundir_blocos_sobrepostos_ou_com_poucas_linhas
from Caps_Detector import first_caps_region, split_blue_q_and_answers  # <-- novo import

def render_preview(pagina, ids, perguntas, blocos_amarelos, caps_rects, out_png, dpi=220):
    pix = pagina.get_pixmap(dpi=dpi, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = pix.width / pdf_w, pix.height / pdf_h

    # IDs (verde)
    for it in ids:
        x0,y0,x1,y1 = it["bbox"]
        cv2.rectangle(img,(int(x0*sx),int(y0*sy)),(int(x1*sx),int(y1*sy)),(0,200,0),2)

    # Perguntas (azul)
    for q in perguntas:
        if not q.get("bbox_pergunta"):
            continue
        rx0,ry0,rx1,ry1 = q["bbox_pergunta"]
        cv2.rectangle(img,(int(rx0*sx),int(ry0*sy)),(int(rx1*sx),int(ry1*sy)),(255,0,0),2)

    # Respostas (ciano)
    for blk in blocos_amarelos:
        bx0,by0,bx1,by1 = blk["rect"]
        cv2.rectangle(img,(int(bx0*sx),int(by0*sy)),(int(bx1*sx),int(by1*sy)),(0,255,255),2)

    # Instruções (vermelho) — uma por cada azul
    for cr in caps_rects or []:
        if cr is None:
            continue
        x0,y0,x1,y1 = cr
        cv2.rectangle(img,(int(x0*sx),int(y0*sy)),(int(x1*sx),int(y1*sy)),(0,0,255),2)
        cv2.putText(img,"INSTRUCAO",(int(x0*sx),max(15,int(y0*sy)-6)),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),2,cv2.LINE_AA)

    cv2.imwrite(out_png, img)
    return out_png

def processar_pdf(pdf_path, dpi=220, center_left_px=185):
    doc  = fitz.open(pdf_path)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = os.path.join(os.path.dirname(pdf_path), f"{base}_out")
    os.makedirs(out_dir, exist_ok=True)

    linhas_txt = []

    for i, pagina in enumerate(doc, start=1):
        ids, _ = localizar_ids_pagina(pagina, ignorar_caixas=True, leftmost_only=True, center_left_px=center_left_px)
        blocos = detectar_blocos_leaders(pagina)
        blocos = fundir_blocos_sobrepostos_ou_com_poucas_linhas(pagina, blocos)
        pergs  = extrair_perguntas_de_ids(pagina, ids, blocos, require_respostas=True)

        caps_rects = []
        for q in pergs:
            bb = q.get("bbox_pergunta")
            ident = q.get("identificador","—")

            if not bb:
                caps_rects.append(None)
                # mesmo sem bbox azul, escreve placeholder
                linhas_txt.append(f"ID: {ident} | Página: {i}\nPergunta:\n\nResposta:")
                continue

            # detetar região de instrução (vermelho) para ESTA caixa azul
            cr = first_caps_region(pagina, bb, blocos)
            caps_rects.append(cr)

            # separar linhas (Pergunta vs Resposta), mantendo ordem
            pergunta_linhas, resposta_linhas = split_blue_q_and_answers(pagina, bb, blocos, caps_rect=cr)

            bloco_txt = []
            bloco_txt.append(f"ID: {ident} | Página: {i}")
            bloco_txt.append("Pergunta:")
            bloco_txt.extend(pergunta_linhas or [""])  # se vazio, deixa linha em branco
            bloco_txt.append("Resposta:")
            bloco_txt.extend(resposta_linhas or [""])

            linhas_txt.append("\n".join(bloco_txt).rstrip())

        # preview
        out_png = os.path.join(out_dir, f"{base}_page{i:02d}_preview.png")
        render_preview(pagina, ids, pergs, blocos, caps_rects, out_png, dpi=dpi)
        print(f"Página {i}: {len(ids)} IDs, {len(pergs)} perguntas -> {out_png}")

    # escrever TXT final
    txt_path = os.path.join(out_dir, f"{base}_perguntas_e_respostas.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(("\n" + "-"*60 + "\n").join(linhas_txt) + "\n")

    print(f"\n✅ Saída: {out_dir}")
    print(f"   • TXT: {txt_path}")
    return out_dir, txt_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ExtrairPDF.py ficheiro.pdf"); sys.exit(1)
    processar_pdf(sys.argv[1])
