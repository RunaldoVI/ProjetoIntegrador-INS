# TableExtractor.py
import re
import fitz
from typing import List, Dict, Tuple
from .identificadores import eh_identificador

# ----------------------- Helpers de coords/texto -----------------------
def _px_to_pdf_rect(pagina, img_shape, rect_px):
    h, w = img_shape[:2]
    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = float(pdf_w)/w, float(pdf_h)/h
    x0,y0,x1,y1 = rect_px
    return fitz.Rect(x0*sx, y0*sy, x1*sx, y1*sy)

def _read_clip_text(page, rect_pdf: fitz.Rect) -> str:
    d = page.get_text("dict", clip=rect_pdf)
    parts=[]
    for b in d.get("blocks", []):
        if b.get("type", 0)!=0: continue
        for l in b.get("lines", []):
            txt="".join(s.get("text","") for s in l.get("spans", []))
            txt=txt.replace("\xa0"," ").strip()
            if txt: parts.append(txt)
    return " ".join(parts).strip()

def _dedup(vals, tol=3):
    vals = sorted(int(round(v)) for v in vals)
    out=[]
    for v in vals:
        if not out or abs(v-out[-1])>tol: out.append(v)
    return out

# ----------------------- Grelha a partir da deteção -----------------------
def _grid_from_detection(det) -> Tuple[list, list]:
    x, y, w, h = det.roi_box
    left, top, right, bottom = det.borders
    Ys = [y+top] + [y+hy for _,hy,_,_ in det.filtered_h] + [y+bottom]
    Xs = [x+left] + [x+vx for vx,_,_,_ in det.filtered_v] + [x+right]
    return _dedup(Xs,3), _dedup(Ys,3)

def _cells_from_grid(Xs, Ys):
    rows=[]
    for r in range(len(Ys)-1):
        row=[]
        for c in range(len(Xs)-1):
            row.append((Xs[c], Ys[r], Xs[c+1], Ys[r+1]))
        rows.append(row)
    return rows

# ----------------------- Separar ID e Texto -----------------------
_ID_TAIL = re.compile(r"\s*(\d+[.)]?)\s*$")  # apanha "1" "1." "2)" no fim

def _split_id_and_text(c1: str, c2: str) -> Tuple[str,str]:
    """
    Regras:
      - Se c1 é só o ID → (c1, c2)
      - Se c1 termina com '... <num>' → (num, c1 sem o num)
      - Caso contrário → (c1, c2) (fallback)
    """
    t1, t2 = (c1 or "").strip(), (c2 or "").strip()
    if eh_identificador(t1):                    # 1) primeira coluna já é o ID
        return t1, t2
    m = _ID_TAIL.search(t1)                    # 2) ID colado ao fim do texto
    if m and eh_identificador(m.group(1)):
        ident = m.group(1).strip()
        texto = _ID_TAIL.sub("", t1).strip()
        return ident, (texto if texto else t2)
    # 3) fallback
    return t1, t2

# ----------------------- Extração linha-a-linha -----------------------
def extract_table_rows_from_page(pagina, page_img_bgr, detections, skip_header=True) -> List[Dict]:
    """
    Devolve linhas: {ident, texto, valores(list[str])} por cada deteção.
    """
    out=[]
    for det in detections:
        Xs, Ys = _grid_from_detection(det)
        rows_px = _cells_from_grid(Xs, Ys)
        if not rows_px: 
            continue

        # detectar cabeçalho
        start = 0
        if skip_header and rows_px:
            r0 = rows_px[0]
            if len(r0) >= 2:
                id_rect = _px_to_pdf_rect(pagina, page_img_bgr.shape, r0[0])
                tx_rect = _px_to_pdf_rect(pagina, page_img_bgr.shape, r0[1])
                c1 = _read_clip_text(pagina, id_rect)
                c2 = _read_clip_text(pagina, tx_rect)
                # Se a 1ª linha NÃO parece dados (sem ID) → é header
                if not eh_identificador(c1) and not eh_identificador(c2):
                    start = 1

        for r in range(start, len(rows_px)):
            rp = rows_px[r]
            if len(rp) < 2: 
                continue
            id_pdf  = _px_to_pdf_rect(pagina, page_img_bgr.shape, rp[0])
            txt_pdf = _px_to_pdf_rect(pagina, page_img_bgr.shape, rp[1])
            c1 = _read_clip_text(pagina, id_pdf)
            c2 = _read_clip_text(pagina, txt_pdf)
            ident, texto = _split_id_and_text(c1, c2)

            valores=[]
            for c in range(2, len(rp)):
                v_pdf = _px_to_pdf_rect(pagina, page_img_bgr.shape, rp[c])
                v = _read_clip_text(pagina, v_pdf).strip()
                valores.append(v)

            if not (ident or texto or any(valores)):
                continue

            out.append({"ident": ident.strip(), "texto": texto.strip(), "valores": valores})
    return out

# ----------------------- Headers + inferência por coluna -----------------------
def get_value_headers_from_detection(pagina, page_img_bgr, det) -> List[str]:
    Xs, Ys = _grid_from_detection(det)
    if len(Ys) < 2 or len(Xs) < 3:
        return []
    headers=[]
    for c in range(2, len(Xs)-1):
        rect_px = (Xs[c], Ys[0], Xs[c+1], Ys[1])
        headers.append(_read_clip_text(pagina, _px_to_pdf_rect(pagina, page_img_bgr.shape, rect_px)).strip())
    return headers

def _norm_token(v: str) -> str:
    v=(v or "").strip()
    if not v: return ""
    m=re.fullmatch(r"\D*(\d+)\D*", v)
    return m.group(1) if m else re.sub(r"\s+"," ", v)

def infer_response_columns(rows: List[Dict], headers: List[str], min_rows:int=4, min_coverage:float=0.6) -> List[Dict]:
    """
    Retorna [{idx, header, token, count, total, coverage, is_response}]
    """
    if not rows: return []
    num_cols = max((len(r.get("valores", [])) for r in rows), default=0)
    out=[]
    total=len(rows)
    for ci in range(num_cols):
        vals=[_norm_token((r.get("valores") or [None]* (ci+1))[ci] if ci < len(r.get("valores", [])) else "") for r in rows]
        freq={}
        for v in vals:
            if not v: continue
            freq[v]=freq.get(v,0)+1
        token, cnt = ("",0) if not freq else max(freq.items(), key=lambda kv: kv[1])
        cov = cnt/total if total else 0.0
        header = headers[ci] if ci < len(headers) else f"Col{ci+1}"
        out.append({"idx": ci, "header": header, "token": token, "count": cnt, "total": total,
                    "coverage": cov, "is_response": (total>=min_rows and cov>=min_coverage and token!="")})
    return out

# ----------------------- Compor "Resposta" por linha -----------------------
def attach_answers_to_rows(rows: List[Dict], inferences: List[Dict]) -> List[Dict]:
    """
    Para cada linha, procura a primeira coluna 'ci' tal que
    _norm_token(valor_da_linha[ci]) == inference[ci].token  (e a inferência é válida).
    Adiciona campos 'resposta' (header) e 'valor' (token).
    """
    inf_map = {inf["idx"]: inf for inf in inferences if inf.get("is_response")}
    for r in rows:
        r["resposta"] = ""
        r["valor"]    = ""
        vals = r.get("valores") or []
        for ci, val in enumerate(vals):
            inf = inf_map.get(ci)
            if not inf: 
                continue
            if _norm_token(val) == inf["token"]:
                r["resposta"] = inf["header"]
                r["valor"]    = inf["token"]
                break
    return rows

# ----------------------- Escrita do TXT -----------------------
def write_table_rows_txt(rows: List[Dict], out_txt_path: str):
    """
    Formato:
      [p.xx] Identificador: <id> : Texto: <texto> : Resposta: <header> : Valores: <valor>
    """
    with open(out_txt_path, "w", encoding="utf-8") as f:
        for r in rows:
            pg = f"[p.{r['pagina']:02d}] " if 'pagina' in r else ""
            ident = (r.get("ident","") or "").replace("\n"," ").strip()
            texto = (r.get("texto","") or "").replace("\n"," ").strip()
            resp  = (r.get("resposta","") or "").replace("\n"," ").strip()
            val   = (r.get("valor","") or "").replace("\n"," ").strip()
            f.write(f"{pg}Identificador: {ident} : Texto: {texto} : Resposta: {resp} : Valores: {val}\n")

# Secção extra (opcional) a apendar no TXT — útil para depuração/relatório
def append_response_inference_to_txt(inferences: List[Dict], out_txt_path: str):
    if not inferences: return
    with open(out_txt_path, "a", encoding="utf-8") as f:
        f.write("\n" + "="*60 + "\nRespostas inferidas (por coluna)\n" + "="*60 + "\n")
        for inf in inferences:
            pct = int(round(inf["coverage"]*100))
            mark = "✓" if inf["is_response"] else "•"
            f.write(f"{mark} {inf['header']} -> {inf['token']} ({inf['count']}/{inf['total']} = {pct}%)\n")
