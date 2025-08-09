# caps_detector.py
import fitz

def _tokenize_alpha(text: str):
    toks, cur = [], []
    for ch in text:
        if ch.isalpha():
            cur.append(ch)
        else:
            if cur:
                toks.append("".join(cur))
                cur = []
    if cur:
        toks.append("".join(cur))
    return toks

def has_mixed_or_lower(text: str, *, min_letters=1) -> bool:
    """True se a linha tiver letras e pelo menos uma minúscula (ou seja, não é 100% CAPS)."""
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) < min_letters:
        return False
    return any(ch.islower() for ch in letters)


def is_caps_line(text: str, *, min_letters=4, token_min_len=2) -> bool:
    """
    Considera CAPS se a linha tiver pelo menos 4 letras
    e **NENHUMA** letra minúscula (a-z). Ignora pontuação/números.
    Evita apanhar 'Besides', 'Enter', etc.
    """
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) < min_letters:
        return False
    return not any(ch.islower() for ch in letters)

def lines_in_rect_dict(page, rect: fitz.Rect):
    """Devolve linhas (bbox, text) dentro de um rect, com ordem top->bottom, left->right."""
    d = page.get_text("dict", clip=rect)
    out = []
    for b in d.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        for l in b.get("lines", []):
            spans = l.get("spans", [])
            if not spans:
                continue
            x0 = min(s["bbox"][0] for s in spans)
            y0 = min(s["bbox"][1] for s in spans)
            x1 = max(s["bbox"][2] for s in spans)
            y1 = max(s["bbox"][3] for s in spans)
            txt = "".join(s["text"] for s in spans).strip()
            out.append({"bbox": fitz.Rect(x0, y0, x1, y1), "text": txt})
    out.sort(key=lambda r: (r["bbox"].y0, r["bbox"].x0))
    return out

def first_caps_region(page, blue_rect, yellow_blocks):
    Rb = blue_rect if isinstance(blue_rect, fitz.Rect) else fitz.Rect(*blue_rect)

    def h_overlap_frac(a: fitz.Rect, b: fitz.Rect) -> float:
        x0 = max(a.x0, b.x0); x1 = min(a.x1, b.x1)
        w = max(0.0, x1 - x0)
        return w / max(1e-6, min(a.width, b.width))

    # 1) escolhe o bloco amarelo alinhado com a azul
    candidatos = []
    for blk in yellow_blocks:
        Ry = blk["rect"] if isinstance(blk["rect"], fitz.Rect) else fitz.Rect(*blk["rect"])
        if Ry.y0 <= Rb.y0:
            continue
        if h_overlap_frac(Ry, Rb) < 0.25:
            continue
        candidatos.append(Ry)
    if not candidatos:
        return None

    tol_y = 2.0
    y_top_yellow = min(r.y0 for r in candidatos) - tol_y

    # 2) linhas dentro da caixa azul
    linhas = lines_in_rect_dict(page, Rb)
    if not linhas:
        return None

    # 3) regra nova: só iniciamos CAPS depois de ver uma linha com minúsculas
    seen_mixed = False
    start_idx = None
    for i, ln in enumerate(linhas):
        if ln["bbox"].y0 >= y_top_yellow:
            break
        txt = ln["text"]
        if has_mixed_or_lower(txt):
            seen_mixed = True
            continue
        if seen_mixed and is_caps_line(txt):
            start_idx = i
            break

    if start_idx is None:
        return None

    y_top = linhas[start_idx]["bbox"].y0
    y_bot = y_top_yellow

    # 4) largura: cobre todas as linhas no intervalo
    xs, xe, max_w, xe_longest = [], [], 0.0, None
    for ln in linhas:
        y0, y1 = ln["bbox"].y0, ln["bbox"].y1
        if y0 < y_bot and y1 > y_top:
            xs.append(ln["bbox"].x0); xe.append(ln["bbox"].x1)
            w = ln["bbox"].x1 - ln["bbox"].x0
            if w > max_w:
                max_w = w; xe_longest = ln["bbox"].x1
    if not xs or xe_longest is None:
        return None

    x0 = max(min(xs), Rb.x0)
    x1 = min(max(max(xe), xe_longest), Rb.x1)
    return fitz.Rect(x0, y_top, x1, y_bot)

def clean_blue_text(page, blue_rect, yellow_blocks, caps_rect=None):
    """
    Texto final dentro da caixa azul, excluindo:
      - qualquer linha que intersecte 'caps_rect' (instruções).
      - mantém o conteúdo dos blocos amarelos (respostas).
    """
    Rb = blue_rect if isinstance(blue_rect, fitz.Rect) else fitz.Rect(*blue_rect)
    linhas = lines_in_rect_dict(page, Rb)

    parts = []
    for ln in linhas:
        if caps_rect and ln["bbox"].intersects(caps_rect):
            continue
        if ln["text"].strip():
            parts.append(ln["text"].strip())
    return " ".join(parts).strip()


def split_blue_q_and_answers(page, blue_rect, yellow_blocks, caps_rect=None,
                             min_overlap_x=0.10, y_merge_tol=2.5):
    """
    Separa a caixa azul em Pergunta e Resposta.
    Para Resposta, funde fragmentos na MESMA 'fila' (quase o mesmo Y).
    """
    Rb = blue_rect if isinstance(blue_rect, fitz.Rect) else fitz.Rect(*blue_rect)

    def h_overlap_frac(a: fitz.Rect, b: fitz.Rect) -> float:
        x0 = max(a.x0, b.x0); x1 = min(a.x1, b.x1)
        w = max(0.0, x1 - x0)
        return w / max(1e-6, min(a.width, b.width))

    def v_overlap_frac(a: fitz.Rect, b: fitz.Rect) -> float:
        y0 = max(a.y0, b.y0); y1 = min(a.y1, b.y1)
        h  = max(0.0, y1 - y0)
        return h / max(1e-6, min(a.height, b.height))

    # amarelos que cruzam a azul (com folga lateral para apanhar os códigos)
    amarelos = []
    for blk in yellow_blocks:
        Ry = blk["rect"] if isinstance(blk["rect"], fitz.Rect) else fitz.Rect(*blk["rect"])
        if not Ry.intersects(Rb) and h_overlap_frac(Ry, Rb) < min_overlap_x:
            continue
        Ry = fitz.Rect(Ry.x0 - 6, Ry.y0 - 2, Ry.x1 + 40, Ry.y1 + 2)  # folga p/ números
        amarelos.append(Ry)

    linhas = lines_in_rect_dict(page, Rb)

    # recolhe fragments Pergunta/Resposta com bboxes
    pergunta_frags, resposta_frags = [], []
    for ln in linhas:
        bb  = ln["bbox"]
        txt = ln["text"].strip()
        if not txt:
            continue
        if caps_rect and bb.intersects(caps_rect):
            continue  # cortar instruções
        # resposta se: boa sobreposição vertical com algum amarelo
        is_answer = any((v_overlap_frac(bb, Ry) >= 0.50) and (bb.x1 >= Ry.x0 - 2) for Ry in amarelos)
        (resposta_frags if is_answer else pergunta_frags).append((bb, txt))

    # --- MERGE por "fila" para RESPOSTAS ---
    # agrupa por y-centro quantizado; dps ordena por x e junta
    def merge_rows(frags):
        if not frags:
            return []
        rows = []
        used = [False]*len(frags)
        for i, (bb, txt) in enumerate(frags):
            if used[i]: 
                continue
            yc = 0.5*(bb.y0 + bb.y1)
            row = [(bb, txt)]; used[i] = True
            for j in range(i+1, len(frags)):
                if used[j]: 
                    continue
                bb2, txt2 = frags[j]
                yc2 = 0.5*(bb2.y0 + bb2.y1)
                if abs(yc2 - yc) <= y_merge_tol:
                    row.append((bb2, txt2)); used[j] = True
            row.sort(key=lambda t: t[0].x0)
            rows.append(" ".join(t for _, t in row))
        return rows

    pergunta = [t for _, t in pergunta_frags]                  # mantém ordem “por linha”
    resposta = merge_rows(resposta_frags)                      # respostas fundidas por fila

    return pergunta, resposta
