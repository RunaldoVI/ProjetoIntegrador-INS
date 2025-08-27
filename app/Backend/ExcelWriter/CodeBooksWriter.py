import re
import pandas as pd
from langdetect import detect, detect_langs, DetectorFactory

DetectorFactory.seed = 0  # garante resultados consistentes

# remove prefixos como "0 -", "1)", "2." etc.
def clean_text(texto: str) -> str:
    return re.sub(r"^\s*\d+\s*[-.)]?\s*", "", (texto or "")).strip()

# detetor robusto
def detectar_idioma(texto: str, default="en") -> str:
    t = (texto or "").strip()
    if not t:
        return "und"
    if len(t) < 15:   # respostas muito curtas dão falsos positivos
        return default
    try:
        langs = detect_langs(t)
        top = max(langs, key=lambda x: x.prob)
        if top.lang == "en":
            return "en"
        return top.lang if top.prob >= 0.92 else default
    except Exception:
        return default

def escrever_codebooks(blocos, writer):
    dados = []

    for bloco in blocos:
        identificador = bloco["Identificador"]
        pergunta = bloco["Pergunta"].strip()

        # Linha da pergunta
        dados.append({
            "hasURI": f"nhanes:CB-{identificador}",
            "hasco:hascoType": "vstoi:Codebook",
            "rdf:type": "vstoi:Codebook",
            "rdfs:label": f"PHQ-9: {pergunta}",
            "vstoi:hasContent": "",
            "vstoi:hasLanguage": detectar_idioma(pergunta),  # análise direta
            "vstoi:hasVersion": "1",
            "rdfs:comment": "",
            "hasco:hasImage": "",
            "hasco:hasWebDocument": ""
        })

        # Linhas das respostas
        for resposta in bloco["Respostas"]:
            texto = resposta["opção"].strip()
            numero = resposta["valor"]

            texto_limpo = clean_text(texto)  # limpa antes de detetar
            idioma = detectar_idioma(texto_limpo)

            dados.append({
                "hasURI": f"nhanes:CB-{identificador}-{numero}",
                "hasco:hascoType": "vstoi:Codebook",
                "rdf:type": "vstoi:Codebook",
                "rdfs:label": f"{numero} - {texto}",  # mantém original
                "vstoi:hasContent": "",
                "vstoi:hasLanguage": idioma,          # idioma do texto limpo
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
