# identificadores.py
import re
import fitz
import cv2
import numpy as np

# Aceita DPQ.010, DMQ.281a, DMQ.281b/c, e variantes com pontuação a seguir
REGEX_ID = re.compile(
    r"^([A-Z]{2,5}[-._]?\d{2,4}(?:[A-Za-z]+(?:[/-][A-Za-z]+)*)?)(?:[:;\]\)\.])?$"
)

def eh_identificador(word: str):
    m = REGEX_ID.match(word.strip())
    return m.group(1) if m else None

# ---------- Caixas (opcional: para ignorar texto dentro) ----------
def detetar_caixas_vetor(pagina, min_w=40, min_h=20):
    caixas = []
    try:
        for d in pagina.get_drawings():
            r = d.get("rect")
            if r and r.width >= min_w and r.height >= min_h:
                caixas.append(r)
            for p in d.get("paths", []):
                if not p.get("closed", False):
                    continue
                rect = p.get("rect")
                if rect:
                    R = fitz.Rect(rect)
                    if R.width >= min_w and R.height >= min_h:
                        caixas.append(R)
    except Exception:
        pass
    return caixas

def detetar_caixas_opencv(pagina, dpi=220, min_w=80, min_h=25, min_area=7000):
    pix = pagina.get_pixmap(dpi=dpi, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 15, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = pdf_w / pix.width, pdf_h / pix.height

    caixas_pdf = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        eps = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, eps, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        x, y, w, h = cv2.boundingRect(approx)
        if x < 5 or y < 5 or x + w > pix.width - 5 or y + h > pix.height - 5:
            continue
        if w < min_w or h < min_h:
            continue
        x0, y0, x1, y1 = x * sx, y * sy, (x + w) * sx, (y + h) * sy
        caixas_pdf.append(fitz.Rect(x0, y0, x1, y1))
    return caixas_pdf

def rect_dentro_de_alguma_caixa(r: fitz.Rect, caixas, margem=2):
    for c in caixas:
        ce = c + (-margem, -margem, margem, margem)
        if ce.contains(r):
            return True
    return False

# ---------- helpers linhas / texto à direita ----------
def _linhas_por_bloco(words):
    linhas = {}
    for w in words:
        b_no = int(w[5]); l_no = int(w[6])
        linhas.setdefault((b_no, l_no), []).append(w)
    for k in linhas:
        linhas[k].sort(key=lambda w: w[0])
    return linhas

def _eh_leftmost_na_linha(candidato, linhas_dict, tol=2.0):
    b_no = int(candidato[5]); l_no = int(candidato[6])
    linha = linhas_dict.get((b_no, l_no), [])
    if not linha:
        return True
    x0_id = float(candidato[0])
    for w in linha:
        if w is candidato:
            continue
        if float(w[0]) < x0_id - tol:
            return False
    return True

def texto_a_direita_mesma_altura(id_rect: fitz.Rect, words,
                                 v_tol=6.0, h_slack=3.0, gap_tol=30.0, max_chars=400):
    yc = 0.5 * (id_rect.y0 + id_rect.y1)
    cand = []
    for (x0, y0, x1, y1, txt, *_ ) in words:
        if not txt.strip():
            continue
        ycw = 0.5 * (y0 + y1)
        if abs(ycw - yc) <= v_tol and x0 >= (id_rect.x1 - h_slack):
            cand.append((x0, y0, x1, y1, txt))
    if not cand:
        return False, "", None
    cand.sort(key=lambda w: w[0])
    cluster = [cand[0]]
    last_x1 = cand[0][2]
    for w in cand[1:]:
        if w[0] - last_x1 > gap_tol:
            break
        cluster.append(w); last_x1 = w[2]
    text = " ".join(w[4] for w in cluster).strip()
    x0 = min(w[0] for w in cluster); y0 = min(w[1] for w in cluster)
    x1 = max(w[2] for w in cluster); y1 = max(w[3] for w in cluster)
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return True, text, [float(x0), float(y0), float(x1), float(y1)]

def texto_a_direita_smart(pagina, id_rect: fitz.Rect, words,
                          dx_slack=20, dx_max=350, dy_up=25, dy_down=120):
    blocks = pagina.get_text("blocks")
    candidatos = []
    for (x0, y0, x1, y1, txt, *_ ) in blocks:
        if not txt or not txt.strip():
            continue
        if y1 < id_rect.y0 - dy_up or y0 > id_rect.y1 + dy_down:
            continue
        dx = x0 - id_rect.x1
        if dx < -dx_slack or dx > dx_max:
            continue
        candidatos.append((abs(dx), y0, fitz.Rect(x0, y0, x1, y1), txt.strip()))
    if not candidatos:
        return False, "", None
    candidatos.sort(key=lambda t: (t[0], t[1]))
    _, _, rect, txt = candidatos[0]
    return True, txt, [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)]

# ---------- API: localizar IDs ----------
def localizar_ids_pagina(pagina,
                         ignorar_caixas=True,
                         leftmost_only=True,
                         left_margin_hint=False,
                         center_left_px=185):
    caixas = []
    if ignorar_caixas:
        caixas = detetar_caixas_vetor(pagina)
        if not caixas:
            caixas = detetar_caixas_opencv(pagina)

    words = pagina.get_text("words")
    words = sorted(words, key=lambda w: (round(w[1]), round(w[0])))
    linhas = _linhas_por_bloco(words)

    resultados = []
    vistos = set()
    for w in words:
        x0, y0, x1, y1, wtext, b_no, l_no, w_no = w
        ident = eh_identificador(wtext)
        if not ident:
            continue
        rect = fitz.Rect(x0, y0, x1, y1)

        # gate: só IDs bem à esquerda do centro
        if center_left_px is not None:
            cx_page = 0.5 * (pagina.rect.x0 + pagina.rect.x1)
            cx_id   = 0.5 * (rect.x0 + rect.x1)
            if cx_id > (cx_page - float(center_left_px)):
                continue

        if ignorar_caixas and rect_dentro_de_alguma_caixa(rect, caixas, margem=2):
            continue
        if leftmost_only and not _eh_leftmost_na_linha(w, linhas, tol=2.0):
            continue
        if left_margin_hint and x0 > pagina.rect.width * 0.30:
            continue

        chave = (ident, int(round(x0)), int(round(y0)))
        if chave in vistos:
            continue
        vistos.add(chave)

        resultados.append({
            "identificador": ident,
            "bbox": [float(x0), float(y0), float(x1), float(y1)],
            "block": int(b_no), "line": int(l_no), "word": int(w_no),
        })
    return resultados, caixas

# ---------- desenho (ids + linhas-guia) ----------
def desenhar_ids(pagina, ids_encontrados, out_png,
                 dpi=220, center_left_px=None, draw_page_center=False,
                 cor_id=(0,200,0)):
    pix = pagina.get_pixmap(dpi=dpi, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = pix.width / pdf_w, pix.height / pdf_h

    cx_page_pdf = 0.5 * (pagina.rect.x0 + pagina.rect.x1)
    if draw_page_center:
        x_center_px = int(cx_page_pdf * sx)
        cv2.line(img, (x_center_px, 0), (x_center_px, pix.height-1), (120,120,120), 1)
        cv2.putText(img, "center", (x_center_px+4, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120,120,120), 1, cv2.LINE_AA)
    if center_left_px is not None:
        x_thr_pdf = cx_page_pdf - float(center_left_px)
        x_thr = int(x_thr_pdf * sx)
        cv2.line(img, (x_thr, 0), (x_thr, pix.height-1), (90,180,255), 2)
        cv2.putText(img, f"center-left {center_left_px:.0f}pt", (x_thr+4, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (90,180,255), 2, cv2.LINE_AA)

    for item in ids_encontrados:
        x0, y0, x1, y1 = item["bbox"]
        p0 = (int(x0*sx), int(y0*sy)); p1 = (int(x1*sx), int(y1*sy))
        cv2.rectangle(img, p0, p1, cor_id, 2)
        cv2.putText(img, item["identificador"], (p0[0], max(15, p0[1]-6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor_id, 2, cv2.LINE_AA)

    cv2.imwrite(out_png, img)
    return out_png
