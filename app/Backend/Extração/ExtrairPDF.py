# ExtrairPDF.py
import os, sys, fitz, cv2, numpy as np
import re
from collections import Counter

from .identificadores import localizar_ids_pagina
from .perguntas import extrair_perguntas_de_ids
from .respostas import detectar_blocos_leaders, fundir_blocos_sobrepostos_ou_com_poucas_linhas
from .Caps_Detector import first_caps_region, split_blue_q_and_answers


# ---------------- Helpers: limpeza e secção linha-a-linha ----------------

# remove runs de pontos/ellipses/bullets/underscore usados como leaders
_LEADER_RE = re.compile(r"[.\u2026•·_]{2,}")

def _limpar_leaders(linha: str) -> str:
    if not linha:
        return ""
    s = _LEADER_RE.sub(" ", linha)      # "....." -> " "
    s = re.sub(r"\s{2,}", " ", s)       # múltiplos espaços -> um
    s = s.strip()
    # garante espaço antes de número final (ex: "texto3" -> "texto 3")
    s = re.sub(r"(\D)(\d+)\s*$", r"\1 \2", s)
    return s

def _norm_line(line: str) -> str:
    """
    Normaliza uma linha para comparação:
    - remove [] exteriores
    - baixa para lower
    - remove pontuação leve :,.;?!(){}"'
    - colapsa espaços
    """
    if not line:
        return ""
    l = line.strip()
    m = re.match(r"^\[\s*(.+?)\s*\]$", l)  # tira colchetes exteriores
    if m:
        l = m.group(1)
    l = l.lower()
    l = re.sub(r'[.,;:?!()\{\}\[\]"“”\'´`]+', '', l)
    l = re.sub(r'\s+', ' ', l).strip()
    return l

def _is_good_candidate(line: str) -> bool:
    """Evita linhas muito curtas/ruído. Pelo menos 5 palavras ou 35 chars."""
    if not line:
        return False
    w = len(re.findall(r'\w+', line))
    return w >= 5 or len(line) >= 35

def _inferir_secao_por_linhas(lista_perguntas_azuis):
    """
    Conta a linha NORMALIZADA mais repetida entre TODAS as perguntas.
    Retorna (secao_bonita, chave_norm, freq).
    """
    counter = Counter()
    exemplar = {}

    for txt in lista_perguntas_azuis or []:
        for raw in str(txt).splitlines():
            raw = raw.strip()
            if not raw or not _is_good_candidate(raw):
                continue
            key = _norm_line(raw)
            if not key:
                continue
            counter[key] += 1
            exemplar.setdefault(key, raw)

    if not counter:
        return None, None, 0

    key_top, freq = counter.most_common(1)[0]
    bonito = exemplar[key_top]
    return bonito, key_top, freq

def _remover_linha_secao(pergunta_texto: str, secao_key_norm: str) -> str:
    """Remove a primeira linha cuja versão normalizada == secao_key_norm."""
    if not pergunta_texto or not secao_key_norm:
        return pergunta_texto or ""
    linhas = [l.rstrip() for l in pergunta_texto.splitlines()]
    out, removed = [], False
    for l in linhas:
        if not removed and _norm_line(l) == secao_key_norm:
            removed = True
            continue
        out.append(l)
    return "\n".join(out).strip()


# ---------------- Render preview ----------------

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

    # Instruções (vermelho)
    for cr in caps_rects or []:
        if cr is None:
            continue
        x0,y0,x1,y1 = cr
        cv2.rectangle(img,(int(x0*sx),int(y0*sy)),(int(x1*sx),int(y1*sy)),(0,0,255),2)
        cv2.putText(img,"INSTRUCAO",(int(x0*sx),max(15,int(y0*sy)-6)),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),2,cv2.LINE_AA)

    cv2.imwrite(out_png, img)
    return out_png


# ---------------- Pipeline principal ----------------

def processar_pdf(pdf_path, dpi=220, center_left_px=185):
    doc  = fitz.open(pdf_path)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = os.path.join(os.path.dirname(pdf_path), f"{base}_out")
    os.makedirs(out_dir, exist_ok=True)

    SEPARADOR = "\n" + "-"*60 + "\n"

    blocos_coletados = []   # {ident, pagina, pergunta_texto, resposta_texto}
    perguntas_azuis = []

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
                blocos_coletados.append({
                    "ident": ident, "pagina": i,
                    "pergunta_texto": "", "resposta_texto": ""
                })
                continue

            # região de instruções (se existir)
            cr = first_caps_region(pagina, bb, blocos)
            caps_rects.append(cr)

            # separa Pergunta/Resposta e SÓ depois faz a limpeza
            pergunta_linhas, resposta_linhas = split_blue_q_and_answers(pagina, bb, blocos, caps_rect=cr)

            pergunta_linhas = [(l or "").strip() for l in (pergunta_linhas or [])]
            resposta_linhas = [_limpar_leaders(l or "") for l in (resposta_linhas or [])]

            pergunta_txt = "\n".join(pergunta_linhas).strip()
            resposta_txt = "\n".join(resposta_linhas).strip()

            blocos_coletados.append({
                "ident": ident, "pagina": i,
                "pergunta_texto": pergunta_txt,
                "resposta_texto": resposta_txt
            })
            if pergunta_txt:
                perguntas_azuis.append(pergunta_txt)

        # preview
        out_png = os.path.join(out_dir, f"{base}_page{i:02d}_preview.png")
        render_preview(pagina, ids, pergs, blocos, caps_rects, out_png, dpi=dpi)
        print(f"Página {i}: {len(ids)} IDs, {len(pergs)} perguntas -> {out_png}")

    # 🧠 inferir Secção pela linha mais repetida entre todas as perguntas
    secao_bonita, secao_key_norm, freq = _inferir_secao_por_linhas(perguntas_azuis)
    total_perg = len(perguntas_azuis)
    if secao_key_norm and freq >= 3 and freq >= max(1, int(0.25 * total_perg)):
        secao_global = secao_bonita
    else:
        secao_global, secao_key_norm = "Nenhuma", None

    print(f"🧠 Secção inferida: {secao_global!r} (freq={freq}, total_perg={total_perg})")

    # escrever TXT final (com Secção e pergunta sem a linha da secção)
    txt_path = os.path.join(out_dir, f"{base}_perguntas_e_respostas.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for b in blocos_coletados:
            pergunta_final = _remover_linha_secao(b["pergunta_texto"], secao_key_norm) if secao_key_norm else b["pergunta_texto"]
            f.write(f"ID: {b['ident']} | Página: {b['pagina']}\n")
            f.write(f"Secção: {secao_global}\n")
            f.write("Pergunta:\n")
            f.write((pergunta_final or "") + "\n")
            f.write("Resposta:\n")
            f.write((b["resposta_texto"] or "") + "\n")
            f.write(SEPARADOR)

    print(f"\n✅ Saída: {out_dir}")
    print(f"   • TXT: {txt_path}")
    return out_dir, txt_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ExtrairPDF.py ficheiro.pdf"); sys.exit(1)
    processar_pdf(sys.argv[1])
