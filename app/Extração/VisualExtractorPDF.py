import fitz  # PyMuPDF
import os

def extrair_blocos_visuais(caminho_pdf, pasta_saida=None):
    if pasta_saida is None:
        pasta_saida = os.path.join(os.path.dirname(__file__), "..", "PDF_Extraido")

    os.makedirs(pasta_saida, exist_ok=True)
    nome_base = os.path.splitext(os.path.basename(caminho_pdf))[0]
    caminho_txt = os.path.join(pasta_saida, f"{nome_base}_fitz_coords.txt")

    doc = fitz.open(caminho_pdf)
    with open(caminho_txt, "w", encoding="utf-8") as f_out:
        for i, pagina in enumerate(doc, start=1):
            blocos = pagina.get_text("blocks")
            f_out.write(f"===== Página {i} =====\n\n")
            for bloco in blocos:
                x0, y0, x1, y1, texto, *_ = bloco
                if texto.strip():
                    f_out.write(f"[{int(x0)}, {int(y0)}, {int(x1)}, {int(y1)}] - {texto.strip()}\n")
            f_out.write("\n")

    return caminho_txt
