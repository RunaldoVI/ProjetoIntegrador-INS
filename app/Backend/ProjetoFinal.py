# ProjetoFinal.py
import sys
import subprocess
import os
import argparse
from PdfViewMode.PreviewMode import executar_preview_todos

print("[DEBUG] Args recebidos:", sys.argv)

parser = argparse.ArgumentParser()
parser.add_argument("caminho_pdf", help="Caminho para o PDF a processar")
parser.add_argument("modo", choices=["preview", "automatico"], help="Modo de execução")
parser.add_argument("instrucoes", nargs="?", default="", help="Instruções extra (apenas no modo preview)")
parser.add_argument("--reuse-preview", action="store_true", help="Reaproveitar dados do preview anterior")
parser.add_argument("--only-ident", type=str, help="Processar apenas o bloco com este Identificador")
parser.add_argument("--only-file", type=str, help="Processar apenas o bloco com este nome de ficheiro JSON")
args = parser.parse_args()

if args.modo == "preview":
    # Instruções extra só se não for o flag --reuse-preview
    instrucoes_extra = args.instrucoes if args.instrucoes != "--reuse-preview" else ""

    # Passar flags novas para a função preview
    executar_preview_todos(
        args.caminho_pdf,
        instrucoes_extra,
        only_ident=args.only_ident,
        only_file=args.only_file,
        reuse_preview=args.reuse_preview
    )

elif args.modo == "automatico":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    auto_path = os.path.join(base_dir, "PdfViewMode", "AutomaticPreviewMode.py")
    cmd = ["python", auto_path, args.caminho_pdf]
    if args.reuse_preview:
        cmd.append("--reuse-preview")
    subprocess.run(cmd, check=True)
else:
    print("❌ Modo inválido. Use 'preview' ou 'automatico'")
