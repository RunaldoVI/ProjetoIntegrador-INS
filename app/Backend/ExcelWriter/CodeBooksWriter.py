import pandas as pd
from langdetect import detect

def escrever_codebooks(blocos, writer):
    dados = []

    for bloco in blocos:
        identificador = bloco["Identificador"]
        ident_norm = identificador.replace(".", "_")
        pergunta = bloco["Pergunta"].strip()

        # Linha da pergunta
        dados.append({
            "hasURI": f"nhanes:CB-{identificador}",
            "hasco:hascoType": "vstoi:Codebook",
            "rdf:type": "vstoi:Codebook",
            "rdfs:label": f"PHQ-9: {pergunta}",
            "vstoi:hasContent": "",
            "vstoi:hasLanguage": detect(pergunta),
            "vstoi:hasVersion": "1",
            "rdfs:comment": "",
            "hasco:hasImage": "",
            "hasco:hasWebDocument": ""
        })

        # Linhas das respostas
        for resposta in bloco["Respostas"]:
            texto = resposta["opção"].strip()
            numero = resposta["valor"]

            dados.append({
                "hasURI": f"nhanes:CB-{identificador}-{numero}",
                "hasco:hascoType": "vstoi:Codebook",
                "rdf:type": "vstoi:Codebook",
                "rdfs:label": f"{numero} - {texto}",
                "vstoi:hasContent": "",
                "vstoi:hasLanguage": detect(texto),
                "vstoi:hasVersion": "1",
                "rdfs:comment": "",
                "hasco:hasImage": "",
                "hasco:hasWebDocument": ""
            })

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

    df.to_excel(writer, sheet_name="CodeBooks", index=False)
