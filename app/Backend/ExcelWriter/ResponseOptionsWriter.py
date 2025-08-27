import re
import pandas as pd
from langdetect import detect, detect_langs, DetectorFactory

DetectorFactory.seed = 0  # resultados reprodutíveis

# remove "0 -", "1.", "2)", etc. do início
def clean_response(texto: str) -> str:
    return re.sub(r"^\s*\d+\s*[-.)]?\s*", "", (texto or "")).strip()

# detetor com pequenas salvaguardas
def safe_detect(texto: str, default="en") -> str:
    t = (texto or "").strip()
    if not t:
        return "und"
    if len(t) < 15:          # muito curto → tende a falhar
        return default
    try:
        langs = detect_langs(t)
        top = max(langs, key=lambda x: x.prob)
        # aceita en mesmo com prob moderada
        if top.lang == "en":
            return "en"
        # só troca do default se houver confiança alta
        return top.lang if top.prob >= 0.92 else default
    except Exception:
        return default

def escrever_responseoptions(blocos, uri_map, writer):
    dados = []
    vistos = set()

    for chave, uri in uri_map.items():
        for bloco in blocos:
            for resposta in bloco["Respostas"]:
                texto = (resposta["opção"] or "").strip()
                numero = resposta["valor"]

                # usar só o TEXTO da resposta para detetar idioma
                texto_limpo = clean_response(texto)
                lang = safe_detect(texto_limpo, default="en")

                normalizado = texto.lower().strip(" .!?")
                if normalizado == chave and chave not in vistos:
                    dados.append({
                        "hasURI": uri,
                        "hasco:hascoType": "FrequencyResponse",
                        "rdf:type": "Response",
                        "rdfs:label": texto,          # mantém label original
                        "vstoi:hasContent": numero,
                        "vstoi:hasLanguage": lang,    # idioma com texto limpo
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
