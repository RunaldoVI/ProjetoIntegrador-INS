import pandas as pd
import json
import os

def carregar_blocos(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def gerar_excel_INS(dados, caminho_saida):
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)

    # Inicializa listas para cada folha
    detectors = []
    codebooks = []
    response_options = []
    codebook_slots = []

    response_uri_counter = 0

    for bloco in dados:
        pergunta_id = bloco.get("identificador", "")
        pergunta_texto = bloco.get("pergunta", "")
        respostas = bloco.get("respostas", [])
        secao = bloco.get("secao", "")

        if not pergunta_id or not pergunta_texto:
            continue

        # --- Detectors ---
        detectors.append({
            "hasURI": f"nhanes:{pergunta_id}",
            "hasco:hasEntity": "nhanes:Person",
            "hasco:hasAttribute": f"nhanes:{pergunta_id}_Attribute",
            "hasco:hasMeasurementStandard": "nhanes:NHANES",
            "rdfs:label": pergunta_texto,
            "vstoi:hasLanguage": "en",
            "vstoi:hasVersion": "1"
        })

        # --- CodeBooks ---
        codebooks.append({
            "hasURI": f"nhanes:{pergunta_id}_Attribute",
            "hasco:hasAttributeLabel": pergunta_texto,
            "hasco:hasAttributeDescription": pergunta_texto,
            "hasco:hasTopic": secao or "General",
            "rdfs:label": pergunta_texto,
            "vstoi:hasLanguage": "en",
            "vstoi:hasVersion": "1"
        })

        # --- ResponseOptions + CodeBookSlots ---
        for r in respostas:
            texto = r.get("texto", "").strip()
            valor = r.get("valor", "").strip()

            if not texto or not valor:
                continue

            uri_resp = f"nhanes:{pergunta_id}_{valor}"

            response_options.append({
                "hasURI": uri_resp,
                "hasco:hascoType": "FrequencyResponse",
                "rdf:type": "Response",
                "rdfs:label": texto,
                "vstoi:hasContent": valor,
                "vstoi:hasLanguage": "en",
                "vstoi:hasVersion": "1"
            })

            codebook_slots.append({
                "hasDetector": f"nhanes:{pergunta_id}",
                "vstoi:hasResponseOption": uri_resp
            })

    # Cria writer Excel com pandas
    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        pd.DataFrame(detectors).to_excel(writer, sheet_name="Detectors", index=False)
        pd.DataFrame(codebooks).to_excel(writer, sheet_name="CodeBooks", index=False)
        pd.DataFrame(response_options).to_excel(writer, sheet_name="ResponseOptions", index=False)
        pd.DataFrame(codebook_slots).to_excel(writer, sheet_name="CodeBookSlots", index=False)

    print(f"Ficheiro Excel criado com sucesso em: {caminho_saida}")


if __name__ == "__main__":
    dados = carregar_blocos("output_blocos_conciliados.json")
    gerar_excel_INS(dados, "INS-gerado/INS-NHANES-DPQ_J.xlsx")
