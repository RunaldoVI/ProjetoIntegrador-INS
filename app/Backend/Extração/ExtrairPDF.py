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

# ================================================================
# Helpers: normalização/limpeza e inferência de secção
# ================================================================

def _singularizar_token(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token

def _normalizar_linha(texto_linha: str) -> str:
    if not texto_linha:
        return ""
    linha = texto_linha.strip()
    colchetes = re.match(r"^\[\s*(.+?)\s*\]$", linha)
    if colchetes:
        linha = colchetes.group(1)
    linha = linha.lower()
    linha = re.sub(r'[.,;:?!()\{\}\[\]"“”\'´`]+', '', linha)
    linha = re.sub(r'\s+', ' ', linha).strip()
    return linha

def _linhas_iguais_normalizadas(a: str, b: str) -> bool:
    a_norm = _normalizar_linha(a)
    b_norm = _normalizar_linha(b)
    if not a_norm or not b_norm:
        return False
    a_norm = " ".join(_singularizar_token(t) for t in a_norm.split())
    b_norm = " ".join(_singularizar_token(t) for t in b_norm.split())
    return a_norm == b_norm

_PADRAO_LEADER = re.compile(r"[.\u2026•·_]{2,}")

def _limpar_leaders(texto_linha: str) -> str:
    if not texto_linha:
        return ""
    limpo = _PADRAO_LEADER.sub(" ", texto_linha)
    limpo = re.sub(r"\s{2,}", " ", limpo)
    limpo = limpo.strip()
    limpo = re.sub(r"(\D)(\d+)\s*$", r"\1 \2", limpo)
    return limpo

def _linha_candidata(texto_linha: str) -> bool:
    if not texto_linha:
        return False
    conta_palavras = len(re.findall(r'\w+', texto_linha))
    return conta_palavras >= 5 or len(texto_linha) >= 35

def _inferir_secao_por_linhas(lista_perguntas_azuis):
    frequencia_por_chave = Counter()
    original_por_chave = {}
    for texto_pergunta in lista_perguntas_azuis or []:
        for linha_bruta in str(texto_pergunta).splitlines():
            linha_bruta = linha_bruta.strip()
            if not linha_bruta or not _linha_candidata(linha_bruta):
                continue
            chave = _normalizar_linha(linha_bruta)
            if not chave:
                continue
            frequencia_por_chave[chave] += 1
            original_por_chave.setdefault(chave, linha_bruta)
    if not frequencia_por_chave:
        return None, None, 0
    chave_topo, frequencia = frequencia_por_chave.most_common(1)[0]
    texto_bonito = original_por_chave[chave_topo]
    return texto_bonito, chave_topo, frequencia

def _desenhar_ids_sobre_imagem(imagem_bgr_pagina: np.ndarray,
                               pagina_pdf,
                               ids_encontrados,
                               cor_id=(0, 200, 0),
                               espessura=2):
    imagem = imagem_bgr_pagina
    altura_img, largura_img = imagem.shape[:2]
    pdf_largura, pdf_altura = pagina_pdf.rect.width, pagina_pdf.rect.height
    escala_x, escala_y = float(largura_img) / pdf_largura, float(altura_img) / pdf_altura
    for id_item in ids_encontrados:
        x0, y0, x1, y1 = id_item["bbox"]
        pt0 = (int(x0 * escala_x), int(y0 * escala_y))
        pt1 = (int(x1 * escala_x), int(y1 * escala_y))
        cv2.rectangle(imagem, pt0, pt1, cor_id, espessura)
        cv2.putText(imagem, id_item.get("identificador", ""), (pt0[0], max(15, pt0[1]-6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor_id, 2, cv2.LINE_AA)
    return imagem

def _remover_linha_secao(texto_pergunta: str, chave_secao_normalizada: str) -> str:
    if not texto_pergunta or not chave_secao_normalizada:
        return texto_pergunta or ""
    linhas = [ln.rstrip() for ln in texto_pergunta.splitlines()]
    linhas_saida, removida = [], False
    for ln in linhas:
        if not removida and _linhas_iguais_normalizadas(ln, chave_secao_normalizada):
            removida = True
            continue
        linhas_saida.append(ln)
    return "\n".join(linhas_saida).strip()

# ================================================================
# Helpers: mapear linha->ID e escrever blocos de tabela
# ================================================================

def _match_id_por_texto(texto_linha: str, blocos_coletados, numero_pagina: int) -> str:
    """
    Mapeia a linha da tabela ao ID 'verde' (ex.: DPQ.010) por similaridade
    com o enunciado dessa mesma página.
    """
    chave = _normalizar_linha(texto_linha or "")
    melhor_id, melhor_score = None, 0
    if not chave:
        return None
    for bloco in blocos_coletados:
        if bloco.get("pagina") != numero_pagina:
            continue
        pergunta_norm = _normalizar_linha(bloco.get("pergunta_texto", ""))
        if not pergunta_norm:
            continue
        tokens = chave.split()
        if not tokens:
            continue
        acertos = sum(1 for t in tokens if t in pergunta_norm)
        score = acertos / max(1, len(tokens))
        if score > melhor_score and score >= 0.5:  # ≥ 50% match
            melhor_score = score
            melhor_id = bloco.get("ident")
    return melhor_id

def _escrever_blocos_tabela_txt(blocos, caminho_txt_saida: str, secao_global: str):
    """
    Escreve blocos no formato:
      ID: <id> | Página: <n>
      Secção: <secao_global>
      Pergunta:
      <texto>
      Resposta:
      <label_1>  <token_1>
      ...
    """
    with open(caminho_txt_saida, "w", encoding="utf-8") as f:
        for bloco in blocos:
            f.write(f"ID: {bloco.get('id','—')} | Página: {bloco.get('pagina','—')}\n")
            f.write(f"Secção: {secao_global or 'Nenhuma'}\n")
            f.write("Pergunta:\n")
            f.write((bloco.get('pergunta','') or '').strip() + "\n")
            f.write("Resposta:\n")
            for (rotulo, codigo) in bloco.get("opcoes", []):
                rotulo = (rotulo or "").strip()
                codigo = (codigo or "").strip()
                if rotulo or codigo:
                    f.write(f"{rotulo}  {codigo}\n")
            f.write("\n" + "-"*60 + "\n")

# ================================================================
# Render preview (quando NÃO há tabela)
# ================================================================

def render_preview(pagina_pdf, ids_detectados, perguntas_detectadas,
                   blocos_resposta, caps_rects, caminho_png, dpi=220):
    pixmap = pagina_pdf.get_pixmap(dpi=dpi, alpha=False)
    imagem = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3).copy()
    pdf_largura, pdf_altura = pagina_pdf.rect.width, pagina_pdf.rect.height
    escala_x, escala_y = pixmap.width / pdf_largura, pixmap.height / pdf_altura

    # IDs (verde)
    for id_box in ids_detectados:
        x0, y0, x1, y1 = id_box["bbox"]
        cv2.rectangle(imagem, (int(x0*escala_x), int(y0*escala_y)), (int(x1*escala_x), int(y1*escala_y)), (0,200,0), 2)

    # Perguntas (azul)
    for q_item in perguntas_detectadas:
        if not q_item.get("bbox_pergunta"):
            continue
        qx0, qy0, qx1, qy1 = q_item["bbox_pergunta"]
        cv2.rectangle(imagem, (int(qx0*escala_x), int(qy0*escala_y)), (int(qx1*escala_x), int(qy1*escala_y)), (255,0,0), 2)

    # Respostas (ciano)
    for bloco_resp in blocos_resposta:
        ax0, ay0, ax1, ay1 = bloco_resp["rect"]
        cv2.rectangle(imagem, (int(ax0*escala_x), int(ay0*escala_y)), (int(ax1*escala_x), int(ay1*escala_y)), (0,255,255), 2)

    # Instruções (vermelho)
    for caps_rect in caps_rects or []:
        if caps_rect is None:
            continue
        x0, y0, x1, y1 = caps_rect
        cv2.rectangle(imagem, (int(x0*escala_x), int(y0*escala_y)), (int(x1*escala_x), int(y1*escala_y)), (0,0,255), 2)
        cv2.putText(imagem, "INSTRUCAO", (int(x0*escala_x), max(15, int(y0*escala_y)-6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2, cv2.LINE_AA)

    cv2.imwrite(caminho_png, imagem)
    return caminho_png

# ================================================================
# Desenho de tabelas (quando HÁ tabela)
# ================================================================

def _construir_overlay_tabelas(imagem_bgr_pagina: np.ndarray,
                               deteccoes: list[TableDetection],
                               tolerancia_px: int = 6,
                               espessura_px: int = 3):
    if not deteccoes:
        return imagem_bgr_pagina
    imagem_combinada = imagem_bgr_pagina.copy()
    for det_tabela in deteccoes:
        imagem_combinada = render_table_overlay(
            imagem_combinada, det_tabela.roi_box, det_tabela.borders,
            det_tabela.filtered_h, det_tabela.filtered_v,
            tolerance_px=tolerancia_px,
            thickness_px=espessura_px
        )
    return imagem_combinada

# ================================================================
# Pipeline principal
# ================================================================

def processar_pdf(caminho_pdf,
                  dpi_preview=220,
                  center_left_px=185,
                  dpi_tabelas=350,
                  min_area_ratio=.02,
                  tolerance_px=6,
                  return_tables_path: bool = False,
                  merge_tables_into_main: bool = True,
                  gerar_txt_tabelas_separado: bool = False):
    documento = fitz.open(caminho_pdf)
    base_name = os.path.splitext(os.path.basename(caminho_pdf))[0]
    pasta_saida = os.path.join(os.path.dirname(caminho_pdf), f"{base_name}_out")
    os.makedirs(pasta_saida, exist_ok=True)

    # --- 1) PRÉ-SCAN ---
    scan = analyze_pdf_all_pages(caminho_pdf, dpi=dpi_tabelas,
                                 min_area_ratio=min_area_ratio, tolerance_px=tolerance_px)
    tabelas_por_pagina = {pagina_idx: (img, dets) for (pagina_idx, img, dets) in scan}

    blocos_coletados = []          # perguntas/respostas (para mapear ID verde)
    perguntas_azuis = []
    todas_linhas_tabela = []       # linhas formatadas (debug/diagnóstico)
    todas_inferencias_resposta = []# inferências por coluna (relatório)
    blocos_tabela = []             # blocos no formato final

    # --- 2) Loop pelas páginas ---
    for indice_pagina, pagina_pdf in enumerate(documento, start=1):
        ids_candidatos, _ = localizar_ids_pagina(
            pagina_pdf, ignorar_caixas=True, leftmost_only=True, center_left_px=center_left_px
        )
        blocos_leaders = detectar_blocos_leaders(pagina_pdf)
        blocos_leaders = fundir_blocos_sobrepostos_ou_com_poucas_linhas(pagina_pdf, blocos_leaders)
        perguntas_de_ids  = extrair_perguntas_de_ids(pagina_pdf, ids_candidatos, blocos_leaders, require_respostas=True)

        rects_caps = []
        for pergunta in perguntas_de_ids:
            bbox_pergunta = pergunta.get("bbox_pergunta")
            identificador = pergunta.get("identificador", "—")
            if not bbox_pergunta:
                rects_caps.append(None)
                blocos_coletados.append({"ident": identificador, "pagina": indice_pagina,
                                         "pergunta_texto": "", "resposta_texto": ""})
                continue

            rect_caps = first_caps_region(pagina_pdf, bbox_pergunta, blocos_leaders)
            rects_caps.append(rect_caps)
            linhas_pergunta, linhas_resposta = split_blue_q_and_answers(pagina_pdf, bbox_pergunta, blocos_leaders, caps_rect=rect_caps)
            texto_pergunta = "\n".join([(ln or "").strip() for ln in (linhas_pergunta or [])]).strip()
            texto_resposta = "\n".join([_limpar_leaders(ln or "") for ln in (linhas_resposta or [])]).strip()
            blocos_coletados.append({"ident": identificador, "pagina": indice_pagina,
                                     "pergunta_texto": texto_pergunta,
                                     "resposta_texto": texto_resposta})
            if texto_pergunta:
                perguntas_azuis.append(texto_pergunta)

        imagem_pagina_bgr, deteccoes = tabelas_por_pagina.get(indice_pagina, (None, []))

        if deteccoes:
            imagem_com_overlay = _construir_overlay_tabelas(
                imagem_pagina_bgr.copy(), deteccoes,
                tolerancia_px=tolerance_px, espessura_px=3
            )

            # 2a) por cada tabela: extrair linhas, inferir colunas de resposta e criar blocos
            for det in deteccoes:
                linhas_detectadas = extract_table_rows_from_page(pagina_pdf, imagem_pagina_bgr, [det], skip_header=True)
                for linha in linhas_detectadas:
                    linha["pagina"] = indice_pagina

                cabecalhos_valor = get_value_headers_from_detection(pagina_pdf, imagem_pagina_bgr, det)
                colunas_inferidas = infer_response_columns(linhas_detectadas, cabecalhos_valor, min_rows=4, min_coverage=0.6)

                # adicionar 'resposta'/'valor' por linha (para o TXT linha-a-linha)
                linhas_detectadas = attach_answers_to_rows(linhas_detectadas, colunas_inferidas)

                # opções da tabela = (header -> token dominante) apenas se existir token
                opcoes = [(inf["header"], inf["token"]) for inf in colunas_inferidas if (inf.get("token"))]

                # acumular (diagnóstico/relatório)
                todas_linhas_tabela.extend(linhas_detectadas)
                todas_inferencias_resposta.extend(colunas_inferidas)

                # construir blocos no formato final
                for linha in linhas_detectadas:
                    id_verde = _match_id_por_texto(linha.get("texto",""), blocos_coletados, indice_pagina) or linha.get("ident","—")
                    blocos_tabela.append({
                        "id": id_verde,
                        "pagina": indice_pagina,
                        "pergunta": linha.get("texto",""),
                        "opcoes": opcoes,
                    })

            # 2b) imagem final com IDs dentro das tabelas (debug)
            ids_dentro_tabelas = []
            altura_img, largura_img = imagem_com_overlay.shape[:2]
            pdf_largura, pdf_altura = pagina_pdf.rect.width, pagina_pdf.rect.height
            escala_x, escala_y = float(largura_img)/pdf_largura, float(altura_img)/pdf_altura
            rects_tabelas_px = []
            for det in deteccoes:
                roi_x, roi_y, roi_w, roi_h = det.roi_box
                left, top, right, bottom = det.borders
                rects_tabelas_px.append((roi_x+left, roi_y+top, roi_x+right, roi_y+bottom))
            def inside_any(px, py, rects):
                return any(x0<=px<=x1 and y0<=py<=y1 for x0,y0,x1,y1 in rects)
            for id_box in ids_candidatos:
                x0, y0, x1, y1 = id_box["bbox"]
                cx_px = ((x0 + x1) / 2.0) * escala_x
                cy_px = ((y0 + y1) / 2.0) * escala_y
                if inside_any(cx_px, cy_px, rects_tabelas_px):
                    ids_dentro_tabelas.append(id_box)
            imagem_final = _desenhar_ids_sobre_imagem(imagem_com_overlay.copy(), pagina_pdf, ids_dentro_tabelas)
            caminho_ids_tabelas = os.path.join(pasta_saida, f"{base_name}_page{indice_pagina:02d}_tables_ids.png")
            cv2.imwrite(caminho_ids_tabelas, imagem_final)
            print(f"Página {indice_pagina}: {len(deteccoes)} tabela(s) -> {caminho_ids_tabelas}")

        else:
            caminho_png = os.path.join(pasta_saida, f"{base_name}_page{indice_pagina:02d}_preview.png")
            render_preview(pagina_pdf, ids_candidatos, perguntas_de_ids, blocos_leaders, rects_caps, caminho_png, dpi=dpi_preview)
            print(f"Página {indice_pagina}: sem tabelas -> {caminho_png}")

    # --- 3) Inferir Secção ---
    texto_secao_bonito, chave_secao_normalizada, frequencia = _inferir_secao_por_linhas(perguntas_azuis)
    total_perguntas = len(perguntas_azuis)
    secao_global = texto_secao_bonito if (chave_secao_normalizada and frequencia >= 3 and frequencia >= max(1, int(0.25 * total_perguntas))) else "Nenhuma"
    if secao_global == "Nenhuma":
        chave_secao_normalizada = None

    print(f"🧠 Secção inferida: {secao_global!r} (freq={frequencia}, total_perg={total_perguntas})")

    # --- 4) Escrever TXT Único: Perg/Resp (azuis) + blocos de tabela ---
    caminho_txt_principal = os.path.join(pasta_saida, f"{base_name}_perguntas_e_respostas.txt")
    with open(caminho_txt_principal, "w", encoding="utf-8") as f:
        # 4a) pipeline clássico (azuis)
        for bloco in blocos_coletados:
            pergunta_final = _remover_linha_secao(bloco["pergunta_texto"], chave_secao_normalizada) if chave_secao_normalizada else bloco["pergunta_texto"]
            f.write(f"ID: {bloco['ident']} | Página: {bloco['pagina']}\n")
            f.write(f"Secção: {secao_global}\n")
            f.write("Pergunta:\n")
            f.write((pergunta_final or "") + "\n")
            f.write("Resposta:\n")
            f.write((bloco["resposta_texto"] or "") + "\n")
            f.write("\n" + "-"*60 + "\n")

        # 4b) blocos vindos de TABELA (sem cabeçalho extra)
        if merge_tables_into_main and blocos_tabela:
            for bloco in blocos_tabela:
                f.write(f"ID: {bloco.get('id','—')} | Página: {bloco.get('pagina','—')}\n")
                f.write(f"Secção: {secao_global or 'Nenhuma'}\n")
                f.write("Pergunta:\n")
                f.write((bloco.get('pergunta','') or '').strip() + "\n")
                f.write("Resposta:\n")
                for (rotulo, codigo) in bloco.get("opcoes", []):
                    rotulo = (rotulo or "").strip()
                    codigo = (codigo or "").strip()
                    if rotulo or codigo:
                        f.write(f"{rotulo}  {codigo}\n")
                f.write("\n" + "-"*60 + "\n")

    # --- 5) (opcional) gerar arquivos de diagnóstico separados ---
    caminho_txt_tabelas = None
    caminho_txt_blocos_tabela = None
    if gerar_txt_tabelas_separado and todas_linhas_tabela:
        caminho_txt_tabelas = os.path.join(pasta_saida, f"{base_name}_tabelas.txt")
        write_table_rows_txt(todas_linhas_tabela, caminho_txt_tabelas)
        if todas_inferencias_resposta:
            append_response_inference_to_txt(todas_inferencias_resposta, caminho_txt_tabelas)

        caminho_txt_blocos_tabela = os.path.join(pasta_saida, f"{base_name}_tabelas_blocos.txt")
        _escrever_blocos_tabela_txt(blocos_tabela, caminho_txt_blocos_tabela, secao_global)

        print(f"   • TXT tabelas (linhas): {caminho_txt_tabelas}")
        print(f"   • TXT tabelas (blocos): {caminho_txt_blocos_tabela}")

    print(f"\n✅ Saída: {pasta_saida}")
    print(f"   • TXT Único: {caminho_txt_principal}")
    if return_tables_path:
        return pasta_saida, caminho_txt_principal, caminho_txt_tabelas
    return pasta_saida, caminho_txt_principal

# ---------------- main ----------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ExtrairPDF.py ficheiro.pdf"); sys.exit(1)
    processar_pdf(sys.argv[1])
