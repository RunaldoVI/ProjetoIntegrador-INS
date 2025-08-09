# respostas.py
import re
import fitz

# ---------- padrões para linhas "estruturais" ----------
LEADER_RUN_RE   = re.compile(r"[.\u2026_]{6,}")      # muitos pontos/…/_ 
FORMFIELD_RE    = re.compile(r"[\|_]{3,}")           # sequências tipo |_| |_| ou |||___ etc.
STRUCTURAL_RE   = re.compile(r"(?:[.\u2026_]{6,}|[\|_]{3,})")

def _linhas_dict(pagina):
    d = pagina.get_text("dict")
    linhas = []
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
            full = "".join(s["text"] for s in spans).strip()
            linhas.append({"bbox":[x0,y0,x1,y1], "spans":spans, "text":full})
    return linhas

def _is_structural_line(txt: str) -> bool:
    t = txt.replace(" ", "")
    return bool(STRUCTURAL_RE.search(t))

def detectar_blocos_leaders(pagina, min_run=6, align_tol=24.0, max_gap_y=40.0):
    """Encontra blocos feitos por linhas 'estruturais' e expande-os para abranger os códigos à direita."""
    # 1) apanhar linhas “estruturais”
    linhas_all = _linhas_dict(pagina)
    linhas = [ln for ln in linhas_all if _is_structural_line(ln["text"])]
    if not linhas:
        return []
    linhas.sort(key=lambda ln: ln["bbox"][1])  # por y

    # 2) agrupar por alinhamento vertical e proximidade em y
    grupos, g = [], [linhas[0]]
    for ln in linhas[1:]:
        prev = g[-1]
        cx_ln   = 0.5*(ln["bbox"][0] + ln["bbox"][2])
        cx_prev = 0.5*(prev["bbox"][0] + prev["bbox"][2])
        y_gap   = ln["bbox"][1] - prev["bbox"][1]
        if abs(cx_ln - cx_prev) <= align_tol and y_gap <= max_gap_y:
            g.append(ln)
        else:
            grupos.append(g)
            g = [ln]
    grupos.append(g)

    # 3) caixa base por grupo (em torno dos leaders)
    blocos = []
    for g in grupos:
        first_bb = g[0]["bbox"]
        last_bb  = g[-1]["bbox"]
        x0 = min(first_bb[0], last_bb[0]) - 4
        y0 = first_bb[1] - 4
        x1 = max(first_bb[2], last_bb[2]) + 4
        y1 = last_bb[3]  + 4
        blocos.append({"rect":[x0,y0,x1,y1], "linhas":g})

    # 4) EXPANSÃO HORIZONTAL: incluir qualquer linha de texto que sobreponha em Y
    def v_overlap_frac(bb1, bb2):
        a0,a1 = bb1[1], bb1[3]
        b0,b1 = bb2[1], bb2[3]
        y0 = max(a0, b0); y1 = min(a1, b1)
        h  = max(0.0, y1 - y0)
        base = max(1e-6, min(a1-a0, b1-b0))
        return h / base

    for blk in blocos:
        x0,y0,x1,y1 = blk["rect"]
        # procura a linha MAIS à direita que se sobrepõe em Y (≥50%)
        for ln in linhas_all:
            bb = ln["bbox"]
            if v_overlap_frac(bb, blk["rect"]) >= 0.50:
                x0 = min(x0, bb[0])
                x1 = max(x1, bb[2])  # <- isto puxa até aos números de código
        # pequena folga lateral
        blk["rect"] = [x0 - 2, y0, x1 + 2, y1]

    return blocos


# ---- fusão de blocos ----
def _intersecao_area(r1, r2):
    ax0, ay0, ax1, ay1 = r1; bx0, by0, bx1, by1 = r2
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    return max(0, ix1 - ix0) * max(0, iy1 - iy0)

def _horizontal_overlap_frac(r1, r2):
    ax0, _, ax1, _ = r1; bx0, _, bx1, _ = r2
    ov = max(0, min(ax1, bx1) - max(ax0, bx0))
    base = max(1e-6, min(ax1-ax0, bx1-bx0))
    return ov / base

def _vertical_gap(r1, r2):
    _, ay0, _, ay1 = r1; _, by0, _, by1 = r2
    if ay1 < by0: return by0 - ay1
    if by1 < ay0: return ay0 - by1
    return 0.0

def _uniao(r1, r2):
    ax0, ay0, ax1, ay1 = r1; bx0, by0, bx1, by1 = r2
    return [min(ax0,bx0), min(ay0,by0), max(ax1,bx1), max(ay1,by1)]

def _contar_linhas_entre(linhas_dict, y_top, y_bot):
    cnt = 0
    for ln in linhas_dict:
        y0, y1 = ln["bbox"][1], ln["bbox"][3]
        if y0 >= y_top and y1 <= y_bot:
            if ln["text"].strip():
                cnt += 1
    return cnt

def fundir_blocos_sobrepostos_ou_com_poucas_linhas(
    pagina, blocos,
    min_h_overlap=0.35,
    max_v_gap=6.0,
    max_v_gap_com_texto=120.0,
    max_linhas_intermedias=2
):
    """Funde blocos se há sobreposição/gap curto ou poucas linhas entre eles."""
    if not blocos:
        return []
    linhas_all = _linhas_dict(pagina)
    items = [{"rect": b["rect"][:], "linhas": list(b.get("linhas", []))} for b in blocos]
    changed = True
    while changed:
        changed = False
        out, used = [], [False]*len(items)
        for i in range(len(items)):
            if used[i]:
                continue
            acc = items[i]
            for j in range(i+1, len(items)):
                if used[j]:
                    continue
                r1, r2 = acc["rect"], items[j]["rect"]
                inter = _intersecao_area(r1, r2) > 0
                hfrac = _horizontal_overlap_frac(r1, r2)
                vgap  = _vertical_gap(r1, r2)
                cond_simple = (vgap <= max_v_gap and hfrac >= min_h_overlap)
                cond_texto  = (vgap <= max_v_gap_com_texto and hfrac >= min_h_overlap and
                               _contar_linhas_entre(linhas_all, min(r1[3], r2[3]), max(r1[1], r2[1])) <= max_linhas_intermedias)
                if inter or cond_simple or cond_texto:
                    acc["rect"] = _uniao(acc["rect"], items[j]["rect"])
                    acc["linhas"].extend(items[j].get("linhas", []))
                    used[j] = True
                    changed = True
            used[i] = True
            out.append(acc)
        items = out
    return items
