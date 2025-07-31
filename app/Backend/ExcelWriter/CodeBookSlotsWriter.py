import pandas as pd

def escrever_codebookslots(blocos, uri_map, writer):
    dados = []

    for bloco in blocos:
        identificador = bloco["Identificador"].replace(".", "_")
        belongs_to = f"nhanes:CB-DPQ_{identificador}"

        for resposta in bloco["Respostas"]:
            texto = resposta["opção"].strip()
            numero = resposta["valor"]
            chave = texto.lower().strip(" .!?")
            uri_resposta = uri_map.get(chave)

            dados.append({
                "hasURI": f"{belongs_to}-{numero}",
                "hasco:hascoType": "vstoi:CodeBookSlots",
                "rdf:type": "vstoi:CodeBookSlots",
                "vstoi:belongsTo": belongs_to,
                "vstoi:hasResponseOption": uri_resposta,
                "vstoi:hasPriority": ""
            })

    df = pd.DataFrame(dados, columns=[
        "hasURI",
        "hasco:hascoType",
        "rdf:type",
        "vstoi:belongsTo",
        "vstoi:hasResponseOption",
        "vstoi:hasPriority"
    ])

    df.to_excel(writer, sheet_name="CodeBookSlots", index=False)
