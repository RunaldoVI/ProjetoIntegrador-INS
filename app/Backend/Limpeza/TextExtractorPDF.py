import fitz  # PyMuPDF
import os
import re
import cv2
import numpy as np

# -----------------------------------------
# Regras de identificação de perguntas
# -----------------------------------------
regex_id = re.compile(r"^([A-Z]{2,5}[-._]?[0-9]{2,4})")

def eh_identificador_valido(texto: str):
    m = regex_id.match(texto)
    if not m:
        return None
    ident = m.group(1)
    resto = texto[len(ident):].strip()
    if "(" in texto and ")" in texto and ident in texto:
        return None
    if len(resto) > 40:
        return None
    return ident

# -----------------------------------------
# Compat helpers (PyMuPDF antigo vs. novo)
# -----------------------------------------
def rect_area(r: fitz.Rect) -> float:
    if hasattr(r, "get_area"):
        return r.get_area()
    if hasattr(r, "getArea"):
        return r.getArea()
    return max(0.0, (r.x1 - r.x0)) * max(0.0, (r.y1 - r.y0))

def rect_is_empty(r: fitz.Rect) -> bool:
    if hasattr(r, "is_empty"):
        return bool(r.is_empty)
    if hasattr(r, "isEmpty"):
        return bool(r.isEmpty)
    return rect_area(r) <= 0.0

# -----------------------------------------
# Geometria / sobreposição
# -----------------------------------------
def iou_pdf(a: fitz.Rect, b: fitz.Rect) -> float:
    inter = a & b
    if rect_is_empty(inter):
        return 0.0
    ai, bi = rect_area(a), rect_area(b)
    inter_a = rect_area(inter)
    return float(inter_a) / float(ai + bi - inter_a + 1e-9)

def bloco_em_caixa(bloco: fitz.Rect, caixas, margem=2, min_overlap=0.55) -> bool:
    cx = (bloco.x0 + bloco.x1) / 2.0
    cy = (bloco.y0 + bloco.y1) / 2.0
    centro = fitz.Point(cx, cy)
    for c in caixas:
        ce = c + (-margem, -margem, margem, margem)
        if ce.contains(centro):
            return True
        if iou_pdf(ce, bloco) >= min_overlap:
            return True
    return False

def unir_caixas(caixas, iou_thresh=0.25):
    if not caixas:
        return []
    caixas = caixas[:]
    caixas.sort(key=lambda r: (r.x0, r.y0))
    out = []
    for r in caixas:
        merged = False
        for i, o in enumerate(out):
            if iou_pdf(r, o) > iou_thresh or rect_area(r & o) > 0:
                out[i] = fitz.Rect(
                    min(r.x0, o.x0), min(r.y0, o.y0),
                    max(r.x1, o.x1), max(r.y1, o.y1)
                )
                merged = True
                break
        if not merged:
            out.append(r)
    return out

# -----------------------------------------
# Deteção de caixas (vetor + OpenCV)
# -----------------------------------------
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

def detetar_caixas_opencv(pagina, dpi=220,
                          min_w=80, min_h=25, min_area=7000,
                          debug=False, debug_dir=None, page_index=1):
    pix = pagina.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 15, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_h, img_w = img.shape[:2]
    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = pdf_w / img_w, pdf_h / img_h

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
        if x < 5 or y < 5 or x + w > img_w - 5 or y + h > img_h - 5:
            continue
        if w < min_w or h < min_h:
            continue
        x0, y0, x1, y1 = x * sx, y * sy, (x + w) * sx, (y + h) * sy
        caixas_pdf.append(fitz.Rect(x0, y0, x1, y1))

    if debug and debug_dir:
        vis = img.copy()
        for c in caixas_pdf:
            rx0, ry0, rx1, ry1 = int(c.x0 / sx), int(c.y0 / sy), int(c.x1 / sx), int(c.y1 / sy)
            cv2.rectangle(vis, (rx0, ry0), (rx1, ry1), (0, 0, 255), 2)
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_index:03d}_caixas.png"), vis)

    return caixas_pdf

# -----------------------------------------
# Limpeza de bloco
# -----------------------------------------
def limpar_bloco(bloco, identificador):
    if identificador and bloco and bloco[0].strip() == identificador:
        bloco = bloco[1:]
    i = 1
    while i < len(bloco):
        atual = bloco[i].strip()
        anterior = bloco[i - 1].strip()
        if atual.isdigit() and len(atual) < 3:
            if "..." in anterior and not re.search(r"\d\s*$", anterior):
                bloco[i - 1] = anterior + " " + atual
                bloco.pop(i)
                continue
        i += 1
    while bloco and bloco[-1].strip().isdigit() and len(bloco[-1].strip()) < 3:
        bloco.pop()
    return bloco

# -----------------------------------------
# NOVO: “intro” -> Secção (inferida por página)
# -----------------------------------------
INTRO_PATTERNS = [
    r"over the last\s+\d+\s+(?:week|weeks|month|months|year|years).*?(?::|\?)",
    r"over the past\s+\d+\s+(?:week|weeks|month|months|year|years).*?(?::|\?)",
    r"during the past\s+\d+\s+(?:week|weeks|month|months|year|years).*?(?::|\?)",
    r"in the past\s+\d+\s+(?:week|weeks|month|months|year|years).*?(?::|\?)",
    r"the following (?:questions|items).*?(?::|\?)",
]
INTRO_RE = re.compile("|".join(f"(?:{p})" for p in INTRO_PATTERNS), re.IGNORECASE)

def _norm_intro(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).rstrip(":?;.,").lower()

def remover_intro_duplicado(texto_bloco: str, intro: str) -> str:
    if not texto_bloco or not intro:
        return texto_bloco
    alvo = _norm_intro(intro)
    linhas = texto_bloco.splitlines()
    out = []
    for idx, l in enumerate(linhas):
        if idx < 3:
            ll = l.strip()
            if ll.startswith("[") and ll.endswith("]"):
                ll = ll[1:-1].strip()
            if _norm_intro(ll) == alvo:
                continue
        out.append(l)
    while out and out[0].strip() == "":
        out.pop(0)
    return "\n".join(out)

def detectar_secao_pagina(blocos_legiveis):
    freq = {}
    canon = {}
    for texto in blocos_legiveis:
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        for l in linhas[:3]:
            m = INTRO_RE.match(l)
            if m:
                intro = m.group(0).strip()
                key = _norm_intro(intro)
                freq[key] = freq.get(key, 0) + 1
                canon[key] = intro
    if not freq:
        return None, 0
    key_top = max(freq, key=freq.get)
    return (canon[key_top], freq[key_top]) if freq[key_top] >= 2 else (None, 0)

# -----------------------------------------
# Pipeline principal
# -----------------------------------------
def extrair_blocos_estruturados(pdf_path, pasta_saida=None, debug_imagens=False):
    """
    Extrai blocos, ignora caixas e injeta 'Secção: ...' inferida por página,
    removendo a linha de intro do corpo do bloco.
    """
    if pasta_saida is None:
        pasta_saida = os.path.join(os.path.dirname(__file__), "..", "PDF_Extraido")
    os.makedirs(pasta_saida, exist_ok=True)

    nome_base = os.path.splitext(os.path.basename(pdf_path))[0]
    caminho_output = os.path.join(pasta_saida, f"{nome_base}_estruturado.txt")
    pasta_debug = os.path.join(pasta_saida, "_debug", nome_base)

    doc = fitz.open(pdf_path)
    blocos_extraidos = []
    bloco_atual = []
    pagina_atual = 0
    identificador_atual = None

    for i, pagina in enumerate(doc, start=1):
        # Caixas: vetor -> OpenCV
        caixas = detetar_caixas_vetor(pagina)
        if not caixas:
            caixas = detetar_caixas_opencv(pagina, debug=debug_imagens,
                                           debug_dir=pasta_debug, page_index=i)
        caixas = unir_caixas(caixas)

        # Prints das caixas e conteúdo
        print(f"\n📄 Página {i}: {len(caixas)} caixa(s) detetadas")
        for idx, c in enumerate(caixas, start=1):
            txt = pagina.get_text("text", clip=c).strip()
            print(f"  ▫️ Caixa {idx}: ({c.x0:.1f}, {c.y0:.1f}) – ({c.x1:.1f}, {c.y1:.1f}) "
                  f"[w={c.width:.1f}, h={c.height:.1f}]")
            print("     Conteúdo:\n" + (txt[:500] + ("…" if len(txt) > 500 else "")).replace("\n", " ") + "\n" if txt else "     (sem texto)\n")

        # 1) Lista de blocos legíveis (fora de caixas)
        blocos = pagina.get_text("blocks")
        blocos_ordenados = sorted(blocos, key=lambda b: (round(b[1]), round(b[0])))
        blocos_legiveis = []
        for b in blocos_ordenados:
            x0, y0, x1, y1, texto_bloco, *_ = b
            texto_bloco = texto_bloco.strip()
            if not texto_bloco:
                continue
            rect_bloco = fitz.Rect(x0, y0, x1, y1)
            if caixas and bloco_em_caixa(rect_bloco, caixas, margem=2, min_overlap=0.55):
                continue
            blocos_legiveis.append(texto_bloco)

        # 2) Inferir secção por página
        secao_pagina, freq = detectar_secao_pagina(blocos_legiveis)
        if secao_pagina:
            print(f"🧩 Secção inferida (pág. {i}, freq={freq}): {secao_pagina}")

        # 3) Processar bloco por bloco
        for texto_bloco in blocos_legiveis:
            texto_bloco = remover_intro_duplicado(texto_bloco, secao_pagina)

            for linha in texto_bloco.splitlines():
                linha = linha.strip()
                if not linha:
                    continue

                novo_id = eh_identificador_valido(linha)
                if novo_id:
                    if bloco_atual:
                        bloco_limpo = limpar_bloco(bloco_atual, identificador_atual)
                        blocos_extraidos.append({
                            "pagina": pagina_atual,
                            "identificador": identificador_atual,
                            "conteudo": "\n".join(bloco_limpo)
                        })
                        bloco_atual = []

                    identificador_atual = novo_id
                    pagina_atual = i
                    bloco_atual.append(linha)

                    # injeta a secção explicitamente (só uma vez por bloco)
                    if secao_pagina:
                        bloco_atual.append(f"Secção: {secao_pagina}")
                else:
                    bloco_atual.append(linha)

    # flush final
    if bloco_atual:
        bloco_limpo = limpar_bloco(bloco_atual, identificador_atual)
        blocos_extraidos.append({
            "pagina": pagina_atual,
            "identificador": identificador_atual,
            "conteudo": "\n".join(bloco_limpo)
        })

    # escrever ficheiro
    with open(caminho_output, "w", encoding="utf-8") as f:
        for b in blocos_extraidos:
            pagina = b['pagina']
            identificador = b['identificador'] if b['identificador'] else "SEM_IDENTIFICADOR"
            f.write(f"[Página {pagina}] - {identificador}\n")
            f.write(f"{b['conteudo']}\n\n")

    print(f"\n✅ Blocos estruturados extraídos para {caminho_output} ({len(blocos_extraidos)} blocos)")
    if debug_imagens:
        print(f"🖼  Imagens de debug guardadas em: {pasta_debug}")
    return caminho_output

# -----------------------------------------
# CLI
# -----------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("❌ Uso: python extrair_blocos_visual.py caminho_para_pdf [--debug]")
        sys.exit(1)
    caminho_pdf = sys.argv[1]
    debug_flag = ("--debug" in sys.argv[2:]) or ("-d" in sys.argv[2:])
    extrair_blocos_estruturados(caminho_pdf, debug_imagens=debug_flag)
