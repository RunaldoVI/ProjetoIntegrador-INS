import pdfplumber
import os

def extrair_texto_para_txt(caminho_pdf, pasta_saida=None):
    if pasta_saida is None:
        pasta_saida = os.path.join(os.path.dirname(os.path.dirname(__file__)), "PDF_Extraido")

    os.makedirs(pasta_saida, exist_ok=True)
    nome_base = os.path.splitext(os.path.basename(caminho_pdf))[0]
    caminho_txt = os.path.join(pasta_saida, f"{nome_base}_extraido.txt")

    with pdfplumber.open(caminho_pdf) as pdf, open(caminho_txt, "w", encoding="utf-8") as f_out:
        for i, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text()
            if texto and texto.strip():
                f_out.write(f"===== Página {i} =====\n\n")
                f_out.write(texto + "\n\n")

    return caminho_txt