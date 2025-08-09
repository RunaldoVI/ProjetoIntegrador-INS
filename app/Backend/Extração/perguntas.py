# perguntas.py
import fitz
import re
import cv2
import numpy as np
from identificadores import texto_a_direita_mesma_altura, texto_a_direita_smart

# regex para identificar respostas (terminam com número) — só usado no fallback
REGEX_RESPOSTA = re.compile(r".*(?:[.\u2026_]{2,}.*\d+|[.\u2026_]+ *\d+)\s*$")

# ---------------- helpers: varrer linhas e medir larguras ----------------
def _linhas_no_intervalo(words, y_top, y_bot, y_tol=0.0):
    """
    Agrupa 'words' por (block_num, line_num) e devolve stats das linhas que
    estão dentro de [y_top, y_bot] (com tolerância opcional).
    Retorna lista de dicts: {x0, x1, y0, y1, width}
    """
    linhas = {}
    for (x0, y0, x1, y1, txt, b_no, l_no, *_ ) in words:
        if not txt or not txt.strip():
            continue
        if y0 >= (y_top - y_tol) and y1 <= (y_bot + y_tol):
            key = (int(b_no), int(l_no))
            d = linhas.setdefault(key, {"x0": x0, "x1": x1, "y0": y0, "y1": y1})
            d["x0"] = min(d["x0"], x0)
            d["x1"] = max(d["x1"], x1)
            d["y0"] = min(d["y0"], y0)
            d["y1"] = max(d["y1"], y1)
    out = []
    for d in linhas.values():
        d["width"] = d["x1"] - d["x0"]
        out.append(d)
    out.sort(key=lambda r: r["y0"])
    return out


def extrair_perguntas_de_ids(
    pagina,
    ids,
    blocos_respostas=None,
    v_tol=6.0,
    require_respostas=True
):
    """
    Para cada ID:
      - encontra a 1ª linha da pergunta à direita;
      - fecha a caixa no 1º bloco de respostas abaixo do ID e *antes do próximo ID*;
      - se require_respostas=True e não houver bloco nesse intervalo, ignora a pergunta.
      - se require_respostas=False, usa um fallback que tenta adivinhar a última linha de resposta.
      - NOVO: X_final da caixa azul = x_right da linha MAIS LONGA dentro do intervalo Y.
    """
    if not ids:
        return []

    # ordenar IDs por Y (topo)
    ids_ord = sorted(ids, key=lambda it: it["bbox"][1])

    # cache de words
    words = pagina.get_text("words")
    words.sort(key=lambda w: (round(w[1], 1), w[0]))

    perguntas = []
    for idx, item in enumerate(ids_ord):
        rect_id = fitz.Rect(*item["bbox"])

        # 1) Primeira linha da pergunta (mesma altura; senão, smart)
        ok, txt, bb = texto_a_direita_mesma_altura(rect_id, words, v_tol=v_tol)
        if not ok:
            ok, txt, bb = texto_a_direita_smart(pagina, rect_id, words)
        if not ok:
            # não conseguimos achar a pergunta — salta
            continue

        y_min = bb[1]
        y_max = bb[3]
        bloco_textos = [txt]

        # 2) Limite inferior = topo do próximo ID (ou fim da página)
        if idx + 1 < len(ids_ord):
            next_y0 = ids_ord[idx + 1]["bbox"][1]
        else:
            next_y0 = pagina.rect.y1

        # 3) Encontrar bloco de respostas nesse intervalo
        bloco_resp = None
        if blocos_respostas:
            candidatos = [
                br for br in blocos_respostas
                if (br["rect"][1] > y_min) and (br["rect"][1] < next_y0)
            ]
            if candidatos:
                # escolher o mais próximo do ID
                bloco_resp = min(candidatos, key=lambda br: br["rect"][1] - y_max)

        # 4) Gate: se for obrigatório ter respostas e não encontrámos, ignora
        if require_respostas and not bloco_resp:
            continue

        if bloco_resp:
            # Fecha Y no fim do bloco de respostas
            y_max = bloco_resp["rect"][3]

            # X_final: linha mais longa dentro de [y_min, y_max]
            y_top_caixa = y_min
            y_bot_caixa = y_max
            linhas = _linhas_no_intervalo(words, y_top_caixa, y_bot_caixa)
            if linhas:
                linha_mais_longa = max(linhas, key=lambda r: r["width"])
                x_max = float(linha_mais_longa["x1"])
            else:
                x_max = float(bb[2])

            # ✅ NOVO: garantir que a caixa azul vai até ao fim do bloco amarelo
            x_max = max(x_max, float(bloco_resp["rect"][2]) + 2.0)  # +2 pt de folga
        else:
            # fallback (apenas quando require_respostas=False):
            # varre até ao próximo ID e tenta achar a última linha "parece resposta"
            ultima_resposta_ymax = None
            for (x0, y0, x1, y1, t, *_ ) in words:
                if y0 >= y_min and y1 <= next_y0:
                    bloco_textos.append(t)
                    y_max = max(y_max, y1)
                    if REGEX_RESPOSTA.match(t.strip()):
                        ultima_resposta_ymax = y1
            if ultima_resposta_ymax:
                y_max = ultima_resposta_ymax

            # NOVO no fallback: também usar a linha mais longa dentro do [y_min, y_max]
            linhas = _linhas_no_intervalo(words, y_min, y_max)
            if linhas:
                x_max = float(max(linhas, key=lambda r: r["width"])["x1"])
            else:
                x_max = float(bb[2])  # último recurso

        # 5) BBox total
        bbox_total = [bb[0], y_min, x_max, y_max]

        perguntas.append({
            "identificador": item["identificador"],
            "bbox_id": item["bbox"],
            "pergunta": " ".join(bloco_textos).strip(),
            "bbox_pergunta": bbox_total
        })

    return perguntas


def desenhar_perguntas(pagina, perguntas, out_png, dpi=220):
    """Desenha as perguntas extraídas: verde para ID, azul para pergunta."""
    pix = pagina.get_pixmap(dpi=dpi, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()

    pdf_w, pdf_h = pagina.rect.width, pagina.rect.height
    sx, sy = pix.width / pdf_w, pix.height / pdf_h

    for p in perguntas:
        # ID em verde
        x0, y0, x1, y1 = p["bbox_id"]
        cv2.rectangle(img, (int(x0*sx), int(y0*sy)), (int(x1*sx), int(y1*sy)), (0, 200, 0), 2)
        cv2.putText(img, p["identificador"], (int(x0*sx), max(15, int(y0*sy)-6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 2, cv2.LINE_AA)

        # Pergunta em azul
        if p.get("bbox_pergunta"):
            bx0, by0, bx1, by1 = p["bbox_pergunta"]
            cv2.rectangle(img, (int(bx0*sx), int(by0*sy)), (int(bx1*sx), int(by1*sy)), (255, 0, 0), 2)
            cv2.putText(img, "Pergunta", (int(bx0*sx), max(15, int(by0*sy)-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2, cv2.LINE_AA)

    cv2.imwrite(out_png, img)
