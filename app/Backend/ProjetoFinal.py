import sys
import subprocess
import os
from PdfViewMode.PreviewMode import executar_preview

if len(sys.argv) < 3:
    print("❌ Uso: python ProjetoFinal.py caminho_para_pdf preview|automatico [instrucoes]")
    sys.exit(1)

caminho_pdf = sys.argv[1]
modo = sys.argv[2].lower()
instrucoes_extra = sys.argv[3] if len(sys.argv) > 3 else ""

# Executa o modo correto
if modo == "preview":
    executar_preview(caminho_pdf, instrucoes_extra)

elif modo == "automatico":
    subprocess.run(["python", "Backend/PdfViewMode/AutomaticPreviewMode.py", caminho_pdf], check=True)

else:
    print("❌ Modo inválido. Use 'preview' ou 'automatico'")
