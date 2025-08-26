# ExtrairPDF.py
import os, sys, cv2, fitz, numpy as np
import re
from collections import Counter
import pandas as pd
import fitz

# ---------- imports do teu projeto ----------
from .identificadores import localizar_ids_pagina
from .perguntas import extrair_perguntas_de_ids
from .respostas import detectar_blocos_leaders, fundir_blocos_sobrepostos_ou_com_poucas_linhas
from .Caps_Detector import first_caps_region, split_blue_q_and_answers

# ---------- ValidateTable (detetar páginas com tabela) ----------
from .ValidateTable import analyze_pdf_all_pages, TableDetection

# ---------- DesenharTabela (desenhar overlays quando há tabela) ----------
from .DesenharTable import render_table_overlay

# ---------- Extração / inferência de tabelas ----------
from .TableExtractor import (
    extract_table_rows_from_page,
    write_table_rows_txt,
    get_value_headers_from_detection,
    infer_response_columns,
    append_response_inference_to_txt,
    attach_answers_to_rows,
)

# ---------------- Helpers: limpeza e secção linha-a-linha ----------------

def _singularize_token(tok: str) -> str:
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok

def _norm_line(line: str) -> str:
    if not line:
        return ""
    l = line.strip()
    m = re.match(r"^\[\s*(.+?)\s*\]$", l)
    if m:
        l = m.group(1)
    l = l.lower()
    l = re.sub(r'[.,;:?!()\{\}\[\]"“”\'´`]+', '', l)
    l = re.sub(r'\s+', ' ', l).strip()
    return l

def _similar_norm_simple(a: str, b: str) -> bool:
    A = _norm_line(a); B = _norm_line(b)
    if not A or not B: return False
    A = " ".join(_singularize_token(t) for t in A.split())
    B = " ".join(_singularize_token(t) for t in B.split())
    return A == B

_LEADER_RE = re.compile(r"[.\u2026•·_]{2,}")

def _limpar_leaders(linha: str) -> str:
    if not linha: return ""
    s = _LEADER_RE.sub(" ", linha)
    s = re.sub(r"\s{2,}", " ", s)
    s = s.strip()
    s = re.sub(r"(\D)(\d+)\s*$", r"\1 \2", s)
    return s

def _is_good_candidate(line: str) -> bool:
    if not line: return False
    w = len(re.findall(r'\w+', line))
    return w >= 5 or len(line) >= 35

def _inferir_secao_por_linhas(lista_perguntas_azuis):
    counter = Counter(); exemplar = {}
    for txt in lista_perguntas_azuis or []:
        for raw in str(txt).splitlines():
            raw = raw.strip()
            if not raw or not _is_good_candidate(raw): continue
            key = _norm_line(raw)
            if not key: continue
            counter[key] += 1
            exemplar.setdefault(key, raw)
    if not counter:
        return None, None, 0
    key_top, freq = counter.most_common(1)[0]
    bonito = exemplar[key_top]
    return bonito, key_top, freq

def _desenhar_ids_sobre_imagem(page_img_bgr: np.ndarray,
                               pagina,
                               ids_encontrados,
                               cor_id=(0, 200, 0),
                               thickness=2):
    img = page_img_bgr
    h, w = img.shape[:2]
    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = float(w) / pdf_w, float(h) / pdf_h
    for item in ids_encontrados:
        x0, y0, x1, y1 = item["bbox"]
        p0 = (int(x0 * sx), int(y0 * sy))
        p1 = (int(x1 * sx), int(y1 * sy))
        cv2.rectangle(img, p0, p1, cor_id, thickness)
        cv2.putText(img, item.get("identificador",""), (p0[0], max(15, p0[1]-6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor_id, 2, cv2.LINE_AA)
    return img

def _remover_linha_secao(pergunta_texto: str, secao_key_norm: str) -> str:
    if not pergunta_texto or not secao_key_norm:
        return pergunta_texto or ""
    linhas = [l.rstrip() for l in pergunta_texto.splitlines()]
    out, removed = [], False
    for l in linhas:
        if not removed and _similar_norm_simple(l, secao_key_norm):
            removed = True
            continue
        out.append(l)
    return "\n".join(out).strip()

# ---------------- Helpers novos: mapear linha->ID e escrever blocos ----------------

def _match_id_por_texto(row_texto: str, blocos_coletados, pagina_num: int) -> str:
    """
    Mapeia a linha da tabela ao ID 'verde' (ex.: DPQ.010) por similaridade com o enunciado dessa página.
    """
    key = _norm_line(row_texto or "")
    melhor_id, melhor_score = None, 0
    if not key:
        return None
    for b in blocos_coletados:
        if b.get("pagina") != pagina_num:
            continue
        per = _norm_line(b.get("pergunta_texto", ""))
        if not per:
            continue
        toks = key.split()
        if not toks:
            continue
        hit = sum(1 for t in toks if t in per)
        score = hit / max(1, len(toks))
        if score > melhor_score and score >= 0.5:  # ≥ 50% match
            melhor_score = score
            melhor_id = b.get("ident")
    return melhor_id

def _write_table_blocks_txt(blocks, out_txt_path: str, secao_global: str):
    """
    Escreve o TXT em blocos:
      ID: <id> | Página: <n>
      Secção: <secao_global>
      Pergunta:
      <texto>
      Resposta:
      <label_1>  <token_1>
      <label_2>  <token_2>
      ...
    (Apenas escreve o que veio da tabela; sem acrescentos automáticos.)
    """
    with open(out_txt_path, "w", encoding="utf-8") as f:
        for bl in blocks:
            f.write(f"ID: {bl.get('id','—')} | Página: {bl.get('pagina','—')}\n")
            f.write(f"Secção: {secao_global or 'Nenhuma'}\n")
            f.write("Pergunta:\n")
            f.write((bl.get('pergunta','') or '').strip() + "\n")
            f.write("Resposta:\n")
            for (label, code) in bl.get("opcoes", []):
                label = (label or "").strip()
                code  = (code or "").strip()
                if label or code:
                    f.write(f"{label}  {code}\n")
            f.write("\n" + "-"*60 + "\n")

# ---------------- Render preview (fluxo normal quando NÃO há tabela) ----------------

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
        if not q.get("bbox_pergunta"): continue
        rx0,ry0,rx1,ry1 = q["bbox_pergunta"]
        cv2.rectangle(img,(int(rx0*sx),int(ry0*sy)),(int(rx1*sx),int(ry1*sy)),(255,0,0),2)

    # Respostas (ciano)
    for blk in blocos_amarelos:
        bx0,by0,bx1,by1 = blk["rect"]
        cv2.rectangle(img,(int(bx0*sx),int(by0*sy)),(int(bx1*sx),int(by1*sy)),(0,255,255),2)

    # Instruções (vermelho)
    for cr in caps_rects or []:
        if cr is None: continue
        x0,y0,x1,y1 = cr
        cv2.rectangle(img,(int(x0*sx),int(y0*sy)),(int(x1*sx),int(y1*sy)),(0,0,255),2)
        cv2.putText(img,"INSTRUCAO",(int(x0*sx),max(15,int(y0*sy)-6)),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),2,cv2.LINE_AA)

    cv2.imwrite(out_png, img)
    return out_png

# ---------------- Desenho de tabelas (quando HÁ tabela) ----------------

def _build_tables_combined(page_image_bgr: np.ndarray,
                           detections: list[TableDetection],
                           tolerance_px: int = 6,
                           thickness_px: int = 3):
    if not detections:
        return page_image_bgr
    combined = page_image_bgr.copy()
    for det in detections:
        combined = render_table_overlay(
            combined, det.roi_box, det.borders,
            det.filtered_h, det.filtered_v,
            tolerance_px=tolerance_px,
            thickness_px=thickness_px
        )
    return combined

# ---------------- Pipeline principal ----------------

def processar_pdf(pdf_path, dpi_preview=220, center_left_px=185,
                  dpi_tabelas=350, min_area_ratio=.02, tolerance_px=6,
                  return_tables_path: bool = False,
                  merge_tables_into_main: bool = True,   # << novo
                  gerar_txt_tabelas_separado: bool = False):  # << novo (debug)
    doc  = fitz.open(pdf_path)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = os.path.join(os.path.dirname(pdf_path), f"{base}_out")
    os.makedirs(out_dir, exist_ok=True)

    # --- 1) PRÉ-SCAN ---
    scan = analyze_pdf_all_pages(pdf_path, dpi=dpi_tabelas,
                                 min_area_ratio=min_area_ratio, tolerance_px=tolerance_px)
    tem_tabela = {p: (img, dets) for (p, img, dets) in scan}

    blocos_coletados = []         # perguntas/respostas (para mapear ID verde)
    perguntas_azuis = []
    linhas_tabelas_all = []       # linhas formatadas (debug/diagnóstico)
    respostas_inferidas_all = []  # inferências por coluna (relatório)
    blocos_tabelas_blocks = []    # <<< novos blocos (formato pedido)

    # --- 2) Loop pelas páginas ---
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
                blocos_coletados.append({"ident": ident, "pagina": i, "pergunta_texto": "", "resposta_texto": ""})
                continue

            cr = first_caps_region(pagina, bb, blocos)
            caps_rects.append(cr)
            pergunta_linhas, resposta_linhas = split_blue_q_and_answers(pagina, bb, blocos, caps_rect=cr)
            pergunta_txt = "\n".join([(l or "").strip() for l in (pergunta_linhas or [])]).strip()
            resposta_txt = "\n".join([_limpar_leaders(l or "") for l in (resposta_linhas or [])]).strip()
            blocos_coletados.append({"ident": ident, "pagina": i,
                                     "pergunta_texto": pergunta_txt,
                                     "resposta_texto": resposta_txt})
            if pergunta_txt:
                perguntas_azuis.append(pergunta_txt)

        page_img_bgr, detections = tem_tabela.get(i, (None, []))

        if detections:
            combined_with_tables = _build_tables_combined(
                page_img_bgr.copy(), detections,
                tolerance_px=tolerance_px, thickness_px=3
            )

            # 2a) PARA CADA TABELA (deteção) — extrair rows, inferir opções e criar blocos
            for det in detections:
                rows_det = extract_table_rows_from_page(pagina, page_img_bgr, [det], skip_header=True)
                for r in rows_det:
                    r["pagina"] = i

                headers = get_value_headers_from_detection(pagina, page_img_bgr, det)
                infs = infer_response_columns(rows_det, headers, min_rows=4, min_coverage=0.6)

                # anexa 'resposta'/'valor' por linha (útil para o TXT linha-a-linha)
                rows_det = attach_answers_to_rows(rows_det, infs)

                # opções desta tabela = pares (header -> token dominante) apenas se token existe
                opcoes = [(inf["header"], inf["token"]) for inf in infs if (inf.get("token"))]

                # acumular (diagnóstico + relatório)
                linhas_tabelas_all.extend(rows_det)
                respostas_inferidas_all.extend(infs)

                # construir blocos no formato pedido
                for r in rows_det:
                    id_verde = _match_id_por_texto(r.get("texto",""), blocos_coletados, i) or r.get("ident","—")
                    blocos_tabelas_blocks.append({
                        "id": id_verde,
                        "pagina": i,
                        "pergunta": r.get("texto",""),
                        "opcoes": opcoes,  # apenas as extraídas da tabela
                    })

            # 2b) imagem final com IDs dentro das tabelas
            ids_in_tables = []
            h, img_w = combined_with_tables.shape[:2]
            pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
            sx, sy = float(img_w)/pdf_w, float(h)/pdf_h
            tables_img = []
            for det in detections:
                x, y, w_roi, h_roi = det.roi_box
                left, top, right, bottom = det.borders
                tables_img.append((x+left, y+top, x+right, y+bottom))
            def inside_any(px, py, rects):
                return any(x0<=px<=x1 and y0<=py<=y1 for x0,y0,x1,y1 in rects)
            for it in ids:
                x0, y0, x1, y1 = it["bbox"]
                cx_px = ((x0 + x1) / 2.0) * sx
                cy_px = ((y0 + y1) / 2.0) * sy
                if inside_any(cx_px, cy_px, tables_img):
                    ids_in_tables.append(it)
            img_final = _desenhar_ids_sobre_imagem(combined_with_tables.copy(), pagina, ids_in_tables)
            out_tables_ids = os.path.join(out_dir, f"{base}_page{i:02d}_tables_ids.png")
            cv2.imwrite(out_tables_ids, img_final)
            print(f"Página {i}: {len(detections)} tabela(s) -> {out_tables_ids}")

        else:
            out_png = os.path.join(out_dir, f"{base}_page{i:02d}_preview.png")
            render_preview(pagina, ids, pergs, blocos, caps_rects, out_png, dpi=dpi_preview)
            print(f"Página {i}: sem tabelas -> {out_png}")

    # --- 3) Inferir Secção ---
    secao_bonita, secao_key_norm, freq = _inferir_secao_por_linhas(perguntas_azuis)
    total_perg = len(perguntas_azuis)
    secao_global = secao_bonita if (secao_key_norm and freq >= 3 and freq >= max(1, int(0.25 * total_perg))) else "Nenhuma"
    if secao_global == "Nenhuma":
        secao_key_norm = None

    print(f"🧠 Secção inferida: {secao_global!r} (freq={freq}, total_perg={total_perg})")

    # --- 4) Escrever TXT Perguntas/Respostas (pipeline clássico) ---
    txt_path = os.path.join(out_dir, f"{base}_perguntas_e_respostas.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        # 4a) pipeline clássico (azuis)
        for b in blocos_coletados:
            pergunta_final = _remover_linha_secao(b["pergunta_texto"], secao_key_norm) if secao_key_norm else b["pergunta_texto"]
            f.write(f"ID: {b['ident']} | Página: {b['pagina']}\n")
            f.write(f"Secção: {secao_global}\n")
            f.write("Pergunta:\n")
            f.write((pergunta_final or "") + "\n")
            f.write("Resposta:\n")
            f.write((b["resposta_texto"] or "") + "\n")
            f.write("\n" + "-"*60 + "\n")

        # 4b) blocos vindos de TABELA, no mesmo formato do *_tabelas_blocos.txt
        if merge_tables_into_main and blocos_tabelas_blocks:
            for bl in blocos_tabelas_blocks:
                f.write(f"ID: {bl.get('id','—')} | Página: {bl.get('pagina','—')}\n")
                f.write(f"Secção: {secao_global or 'Nenhuma'}\n")
                f.write("Pergunta:\n")
                f.write((bl.get('pergunta','') or '').strip() + "\n")
                f.write("Resposta:\n")
                for (label, code) in bl.get("opcoes", []):
                    label = (label or "").strip()
                    code  = (code  or "").strip()
                    if label or code:
                        f.write(f"{label}  {code}\n")
                f.write("\n" + "-"*60 + "\n")

    # --- 5) (opcional) gerar arquivos de diagnóstico separados ---
    txt_tables_path = None
    txt_tables_blocks_path = None
    if gerar_txt_tabelas_separado and linhas_tabelas_all:
        # (a) linha-a-linha (diagnóstico)
        txt_tables_path = os.path.join(out_dir, f"{base}_tabelas.txt")
        write_table_rows_txt(linhas_tabelas_all, txt_tables_path)
        if respostas_inferidas_all:
            append_response_inference_to_txt(respostas_inferidas_all, txt_tables_path)

        # (b) blocos (mesmo conteúdo que já foi fundido no principal)
        txt_tables_blocks_path = os.path.join(out_dir, f"{base}_tabelas_blocos.txt")
        _write_table_blocks_txt(blocos_tabelas_blocks, txt_tables_blocks_path, secao_global)

        print(f"   • TXT tabelas (linhas): {txt_tables_path}")
        print(f"   • TXT tabelas (blocos): {txt_tables_blocks_path}")

    print(f"\n✅ Saída: {out_dir}")
    print(f"   • TXT Único: {txt_path}")
    if return_tables_path:
        return out_dir, txt_path, txt_tables_path
    return out_dir, txt_path

# ---------------- main ----------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ExtrairPDF.py ficheiro.pdf"); sys.exit(1)
    processar_pdf(sys.argv[1])
