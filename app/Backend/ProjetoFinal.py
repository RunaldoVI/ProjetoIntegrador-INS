# ProjetoFinal.py
import sys
import subprocess
import os

from PdfViewMode.PreviewMode import executar_preview

print("[DEBUG] Args recebidos:", sys.argv)

if len(sys.argv) < 3:
    print("❌ Uso: python ProjetoFinal.py caminho_para_pdf preview|automatico [instrucoes|--reuse-preview]")
    sys.exit(1)

caminho_pdf = sys.argv[1]
modo = sys.argv[2].lower()

# pode vir um 3º argumento:
#  - preview: instruções extra (string)
#  - automatico: flag --reuse-preview
extra_arg = sys.argv[3] if len(sys.argv) > 3 else ""

if modo == "preview":
    instrucoes_extra = extra_arg if extra_arg != "--reuse-preview" else ""
    executar_preview(caminho_pdf, instrucoes_extra)

elif modo == "automatico":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    auto_path = os.path.join(base_dir, "PdfViewMode", "AutomaticPreviewMode.py")
    args = ["python", auto_path, caminho_pdf]
    if extra_arg.strip().lower() == "--reuse-preview":
        args.append("--reuse-preview")
    subprocess.run(args, check=True)

else:
    print("❌ Modo inválido. Use 'preview' ou 'automatico'")
