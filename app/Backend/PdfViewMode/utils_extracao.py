# utils_extracao.py
import json
import re
from typing import Tuple, Optional, Dict, Any, List
from LLM.PromptLLM import enviar_pagina_para_llm

ID_LINHA_RE = re.compile(r"^\s*ID:\s*(?P<id>[^|]+)\|\s*Página:\s*(?P<pag>\d+)\s*$", re.IGNORECASE)

# ------------------- helpers: respostas do TXT -------------------

def _parse_respostas(bloco_respostas: str) -> List[Dict[str, str]]:
    """
    Extrai pares opção/valor do texto das respostas.
    Aceita formatos comuns:
      - "0 - Not at all"
      - "Not at all (0)"
      - "1) Several days"
      - "2. More than half the days"
    """
    linhas = [l.strip() for l in (bloco_respostas or "").splitlines() if l.strip()]
    pares = []

    for l in linhas:
        # 1) "0 - Texto"
        m = re.match(r"^\s*(?P<v>\d+)\s*[-:]\s*(?P<op>.+?)\s*$", l)
        if m:
            pares.append({"opção": m.group("op").strip(), "valor": m.group("v").strip()})
            continue

        # 2) "Texto (0)"  / "Texto [0]"
        m = re.match(r"^\s*(?P<op>.+?)\s*[\(\[]\s*(?P<v>\d+)\s*[\)\]]\s*$", l)
        if m:
            pares.append({"opção": m.group("op").strip(), "valor": m.group("v").strip()})
            continue

        # 3) "1) Texto" ou "2. Texto"
        m = re.match(r"^\s*(?P<v>\d+)[\)\.]\s*(?P<op>.+?)\s*$", l)
        if m:
            pares.append({"opção": m.group("op").strip(), "valor": m.group("v").strip()})
            continue

    return pares

def _respostas_validas(respostas):
    return [r for r in (respostas or []) if r.get("opção", "").strip() and r.get("valor", "").strip()]

# ------------------- helpers: parse do bloco TXT -------------------

def _parse_bloco_extrairpdf(bloco: str, secao_geral: str) -> Optional[Dict[str, Any]]:
    """
    Interpreta o bloco no formato produzido pelo ExtrairPDF:
        ID: <ident> | Página: N
        Pergunta:
        <linhas...>
        Resposta:
        <linhas...>
    """
    if not bloco or len(bloco.strip()) < 20:
        return None

    linhas = [l.rstrip("\n") for l in bloco.splitlines()]
    ident = ""
    # 1) Identificador (linha 0 normalmente)
    if linhas:
        m = ID_LINHA_RE.match(linhas[0])
        if m:
            ident = m.group("id").strip()

    # fallback: tenta apanhar algo tipo "DPQ.100"
    if not ident:
        m = re.search(r"\b[A-Z]{2,}\.\d{2,3}[A-Za-z]*\b", bloco)
        if m:
            ident = m.group(0)

    # 2) Encontrar as secções Pergunta/Resposta
    def _indice(prefix):
        for i, l in enumerate(linhas):
            if l.strip().lower().startswith(prefix):
                return i
        return -1

    i_p = _indice("pergunta")
    i_r = _indice("resposta")

    if i_p == -1:
        return None

    texto_pergunta = "\n".join(l.strip() for l in linhas[i_p + 1:(i_r if i_r != -1 else None)]).strip()
    texto_resposta = "\n".join(l.strip() for l in linhas[i_r + 1:]).strip() if i_r != -1 else ""

    if not texto_pergunta:
        return None

    respostas = _parse_respostas(texto_resposta) if texto_resposta else []

    return {
        "Identificador": ident,
        "Secção": secao_geral or "Nenhuma",
        "Pergunta": texto_pergunta,
        "Respostas": respostas,
    }

# ------------------- helpers: JSON do LLM -------------------

def _extrair_json_robusto(texto: str):
    """
    Extrai um objeto JSON do texto do LLM:
      - remove code fences
      - pega do primeiro '{' ao último '}'
      - corrige vírgulas antes de ']' ou '}'
    """
    if not isinstance(texto, str):
        try:
            return json.loads(texto)
        except Exception:
            return None

    s = texto.strip()
    # remove fences de código
    s = re.sub(r"^```(?:json)?", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"```$", "", s).strip()

    i = s.find("{")
    j = s.rfind("}")
    if i == -1 or j == -1 or j < i:
        return None
    blob = s[i:j+1]

    # corrigir vírgulas finais
    blob = re.sub(r",\s*]", "]", blob)
    blob = re.sub(r",\s*}", "}", blob)

    try:
        return json.loads(blob)
    except Exception:
        blob2 = blob.encode("utf-8", "ignore").decode("utf-8", "ignore")
        try:
            return json.loads(blob2)
        except Exception:
            return None

def _normalizar_campos(d: Dict[str, Any]) -> Dict[str, Any]:
    """Aceita 'ID'/'id' e mapeia para 'Identificador'."""
    if not isinstance(d, dict):
        return d
    if "Identificador" not in d:
        if "ID" in d:
            d["Identificador"] = str(d.pop("ID")).strip()
        elif "id" in d:
            d["Identificador"] = str(d.pop("id")).strip()
    return d

# ------------------- API principal -------------------

def processar_bloco(
    bloco: str,
    pergunta: str,
    secao_geral: str,
    preview_identificador: str = None
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Processa um bloco textual do ExtrairPDF:
      - constrói a estrutura local (sem Limpeza/PreProcessamento)
      - envia o bloco bruto ao LLM com o prompt 'pergunta'
      - se o LLM responder bem, devolve (estrutura, resposta_llm); caso contrário (None, None)
    """
    if not bloco or len(bloco.strip()) < 20:
        return None, None

    estrutura = _parse_bloco_extrairpdf(bloco, secao_geral)
    if not estrutura:
        print("❌ Parser do ExtrairPDF falhou em construir estrutura.")
        return None, None

    if preview_identificador and estrutura.get("Identificador", "").strip() == preview_identificador:
        print(f"⏭️  Ignorado (mesmo identificador do preview: {preview_identificador})")
        return None, None

    # ✅ Usa sempre o LLM
    resposta_llm_raw = enviar_pagina_para_llm(bloco, pergunta)

    # Parse robusto do JSON
    resposta_llm = _extrair_json_robusto(resposta_llm_raw)
    if resposta_llm is None:
        print("⚠️ Falha a extrair JSON da resposta do LLM.")
        return None, None

    # Aceita:
    #  a) {"Identificador": "...", ...}
    #  b) {"DPQ.100": {...}}  -> escolhe o 1º (preview trabalha 1 bloco)
    if isinstance(resposta_llm, dict) and resposta_llm and all(isinstance(v, dict) for v in resposta_llm.values()):
        ident = next(iter(resposta_llm))
        corpo = dict(resposta_llm[ident])
        corpo["Identificador"] = corpo.get("Identificador", ident)
        resposta_llm = corpo

    resposta_llm = _normalizar_campos(resposta_llm)

    # validação mínima
    if (
        isinstance(resposta_llm, dict)
        and str(resposta_llm.get("Pergunta", "")).strip()
        and isinstance(resposta_llm.get("Respostas"), list)
        and _respostas_validas(resposta_llm.get("Respostas"))
    ):
        print("🤖 A usar resposta do LLM (válida)")
        return estrutura, resposta_llm

    print("⚠️ LLM respondeu mal ou incompleto. Ignorado.")
    return None, None
