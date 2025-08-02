import sys
import subprocess
import os

if len(sys.argv) < 3:
    print("❌ Uso: python ProjetoFinal.py caminho_para_pdf preview|automatico")
    sys.exit(1)

caminho_pdf = sys.argv[1]
modo = sys.argv[2].lower()

# Limpa preview anterior (opcional)
if modo == "preview" and os.path.exists("preview_output.json"):
    os.remove("preview_output.json")

# Invoca o modo correto
if modo == "preview":
    subprocess.run(["python", "Backend/PdfViewMode/PreviewMode.py", caminho_pdf], check=True)
elif modo == "automatico":
    subprocess.run(["python", "Backend/PdfViewMode/AutomaticPreviewMode.py", caminho_pdf], check=True)
else:
    print("❌ Modo inválido. Use 'preview' ou 'automatico'")
