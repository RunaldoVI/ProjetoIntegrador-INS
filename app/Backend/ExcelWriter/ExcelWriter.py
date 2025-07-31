import os
import json
import pandas as pd
from DetectorsWriter import escrever_detectors
from CodeBooksWriter import escrever_codebooks
from CodeBookSlotsWriter import escrever_codebookslots
from ResponseOptionsWriter import escrever_responseoptions

json_path = "output_blocos_conciliados.json"
excel_path = "pdfs-excels/INS-NHANES-DPQ_J.xlsx"

# Verificar se Excel existe
if not os.path.exists(excel_path):
    raise FileNotFoundError(f"Ficheiro Excel '{excel_path}' não encontrado.")

# Carregar blocos
with open(json_path, encoding="utf-8") as f:
    blocos = json.load(f)

# Criar uri_map global (deduplicado)
uri_map = {}
resposta_global_id = 0
for bloco in blocos:
    for resposta in bloco["Respostas"]:
        chave = resposta["opção"].lower().strip(" .!?")
        if chave not in uri_map:
            uri_map[chave] = f"nhanes:DPQ_{resposta_global_id}"
            resposta_global_id += 1

print(f"📁 A escrever em: {os.path.abspath(excel_path)}")
print(f"📊 Blocos carregados: {len(blocos)}")
print(f"🔗 Total de URIs únicas: {len(uri_map)}")

# Escrever nas folhas do Excel existente
with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    escrever_detectors(blocos, writer)
    escrever_codebooks(blocos, writer)
    escrever_codebookslots(blocos, uri_map, writer)
    escrever_responseoptions(blocos, uri_map, writer)

print("✅ Folhas atualizadas com sucesso no ficheiro INS!")
