import pandas as pd

def escrever_detectors(blocos, writer):
    dados = []

    for bloco in blocos:
        identificador = bloco["Identificador"]
        pergunta = bloco["Pergunta"].strip()

        dados.append({
            "hasURI": identificador,
            "hasco:hascoType": "Detector",
            "a": "",  # só preenchido na linha genérica (linha 1)
            "rdfs:label": pergunta,
            "vstoi:hasDetectorStem": "DETSTEM-GENERIC-DETECTOR",
            "vstoi:hasCodebook": ""  # vazio, como no ficheiro original
        })

    df = pd.DataFrame(dados, columns=[
        "hasURI",
        "hasco:hascoType",
        "a",
        "rdfs:label",
        "vstoi:hasDetectorStem",
        "vstoi:hasCodebook"
    ])

    df.to_excel(writer, sheet_name="Detectors", index=False)