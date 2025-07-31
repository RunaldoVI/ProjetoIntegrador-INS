import pandas as pd
from langdetect import detect

def escrever_responseoptions(blocos, uri_map, writer):
    dados = []
    vistos = set()

    for chave, uri in uri_map.items():
        for bloco in blocos:
            for resposta in bloco["Respostas"]:
                texto = resposta["opção"].strip()
                numero = resposta["valor"]
                normalizado = texto.lower().strip(" .!?")

                if normalizado == chave and chave not in vistos:
                    dados.append({
                        "hasURI": uri,
                        "hasco:hascoType": "FrequencyResponse",
                        "rdf:type": "Response",
                        "rdfs:label": texto,
                        "vstoi:hasContent": numero,
                        "vstoi:hasLanguage": detect(texto),
                        "vstoi:hasVersion": "1",
                        "rdfs:comment": "",
                        "hasco:hasImage": "",
                        "hasco:hasWebDocument": ""
                    })
                    vistos.add(chave)

    df = pd.DataFrame(dados, columns=[
        "hasURI",
        "hasco:hascoType",
        "rdf:type",
        "rdfs:label",
        "vstoi:hasContent",
        "vstoi:hasLanguage",
        "vstoi:hasVersion",
        "rdfs:comment",
        "hasco:hasImage",
        "hasco:hasWebDocument"
    ])

    df.to_excel(writer, sheet_name="ResponseOptions", index=False)
