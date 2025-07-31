import os
import json
import pandas as pd
from .DetectorsWriter import escrever_detectors
from .CodeBooksWriter import escrever_codebooks
from .CodeBookSlotsWriter import escrever_codebookslots
from .ResponseOptionsWriter import escrever_responseoptions

def executar():
    json_path = "output_blocos_conciliados.json"
    excel_path = "pdfs-excels/INS-NHANES-DPQ_J.xlsx"

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Ficheiro Excel '{excel_path}' não encontrado.")

    with open(json_path, encoding="utf-8") as f:
        blocos = json.load(f)

    uri_map = {}
    resposta_global_id = 0
    for bloco in blocos:
        for resposta in bloco["Respostas"]:
            chave = resposta["opção"].lower().strip(" .!?")
            if chave not in uri_map:
                uri_map[chave] = f"nhanes:DPQ_{resposta_global_id}"
                resposta_global_id += 1

    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        escrever_detectors(blocos, writer)
        escrever_codebooks(blocos, writer)
        escrever_codebookslots(blocos, uri_map, writer)
        escrever_responseoptions(blocos, uri_map, writer)

    print("📊 A gerar Excel com base nos blocos conciliados...")
    print(f"\n📁 A escrever em: {os.path.abspath(excel_path)}")
    print("✅ Folhas atualizadas com sucesso no ficheiro INS!")

# Só executa se correr diretamente (não em import)
if __name__ == "__main__":
    executar()
