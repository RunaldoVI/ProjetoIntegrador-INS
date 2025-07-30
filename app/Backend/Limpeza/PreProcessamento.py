import re

def identificar_secao_mais_comum(paginas_texto):
    padrao_secao = re.compile(r"\[.*?\]")
    contagem = {}
    for pagina in paginas_texto:
        matches = padrao_secao.findall(pagina)
        for m in matches:
            m_limpo = m.strip()
            contagem[m_limpo] = contagem.get(m_limpo, 0) + 1
    if not contagem:
        return None
    secao_mais_comum = max(contagem.items(), key=lambda x: x[1])[0]
    print(f"\n🔎 Secção mais comum detetada: {secao_mais_comum}")
    return secao_mais_comum

# Função para segmentar e limpar blocos por identificador
def extrair_blocos_limpos(texto_pagina):
    linhas = texto_pagina.splitlines()
    blocos = []
    bloco_atual = []
    identificador_regex = re.compile(r"^[A-Z]{2,5}\.\d{3}")

    def linha_util(l):
        return not re.match(r"^(BOX|CAPI|CHECK ITEM|INSTRUCTION|SOFT EDIT|HARD EDIT|ERROR MESSAGE|HAND ?CARD|REFUSED|DON'T KNOW|OTHERWISE|GO TO|IF RESPONSE)", l, re.IGNORECASE)

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        if identificador_regex.match(linha):
            if bloco_atual:
                blocos.append("\n".join(bloco_atual))
                bloco_atual = []
            bloco_atual.append(linha)
        elif bloco_atual and linha_util(linha):
            bloco_atual.append(linha)

    if bloco_atual:
        blocos.append("\n".join(bloco_atual))

    return blocos

# Função para separar pergunta e respostas do bloco
def separar_pergunta_respostas(bloco, secao_geral):
    linhas = bloco.splitlines()
    identificador = ""
    pergunta = ""
    respostas = []
    secao_local = None

    id_regex = re.compile(r"^([A-Z]{2,5}\.\d{3})")
    secao_regex = re.compile(r"\[(.*?)\]")
    resp_regex = re.compile(r".*[\.\(]\s*(\d+)\s*\)?$")

    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if i == 0 and id_regex.match(linha):
            identificador = id_regex.match(linha).group(1)
            pergunta = linha[len(identificador):].strip()
            match_secao = secao_regex.search(pergunta)
            if match_secao:
                secao_local = match_secao.group(1).strip()
        elif i > 0 and not resp_regex.match(linha):
            pergunta += " " + linha
        elif resp_regex.match(linha):
            respostas.append(linha)

    secao_final = None
    if secao_local:
        secao_final = secao_local
    elif secao_geral and pergunta.startswith(secao_geral):
        secao_final = secao_geral.strip("[]")
        pergunta = pergunta.replace(secao_geral, "").strip()

    respostas_formatadas = []
    for r in respostas:
        m = re.match(r"(.*?)[\.,:]?\s*\(?([0-9])\)?$", r.strip())
        if m:
            texto = re.sub(r"[\.,:;!?\s]+$", "", m.group(1).strip()).capitalize()
            valor = m.group(2).strip()
            if not re.search(r"(IF RESPONSE|GO TO|CONTINUE|OTHERWISE|BOX)", texto, re.IGNORECASE):
                respostas_formatadas.append({"opção": texto, "valor": valor})

    # NOVO: Inserir "Refused" se estiver no texto original mas não detetado
    valores_existentes = [r["valor"] for r in respostas_formatadas]
    if "9" in valores_existentes and "7" not in valores_existentes:
        texto_original = "\n".join(linhas)
        if re.search(r"\bRefused\b.*[^\d]7[^\d]?", texto_original, re.IGNORECASE):
            respostas_formatadas.insert(-1, {"opção": "Refused", "valor": "7"})

    if not respostas_formatadas and re.search(r"(GO TO NEXT SECTION|CHECK ITEM|BOX)", pergunta, re.IGNORECASE):
        return None

    return {
        "Identificador": identificador,
        "Secção": secao_final if secao_final else "Nenhuma",
        "Pergunta": pergunta.strip(),
        "Respostas": respostas_formatadas
    }

# Função para limpar e normalizar o JSON vindo do LLM
def limpar_estrutura_json(json_obj):
    if isinstance(json_obj, dict):
        pergunta = json_obj.get("Pergunta", "")
        pergunta = re.sub(r"\bHAND\s*C?ARD DPQ\d*\b", "", pergunta, flags=re.IGNORECASE)
        pergunta = re.sub(r"()", "", pergunta)
        pergunta = re.sub(r"[?.!…]\s*\d+$", "", pergunta)
        pergunta = pergunta.strip()

        if re.match(r"^(OTHERWISE, GO TO|CHECK ITEM|BOX|IF RESPONSE|CONTINUE|GO TO)", pergunta, re.IGNORECASE):
            return None

        json_obj["Pergunta"] = pergunta

        respostas = json_obj.get("Respostas", [])
        respostas_limpa = []
        for r in respostas:
            if isinstance(r, dict):
                opcao = r.get("opção", "").strip()
                opcao = re.sub(r"^[-•\s]*", "", opcao)
                opcao = re.sub(r"[\.,:;!?\s]+$", "", opcao).capitalize()
                valor = str(r.get("valor", "")).strip()
                if opcao and valor and not re.search(r"(IF RESPONSE|GO TO|CONTINUE|OTHERWISE|BOX)", opcao, re.IGNORECASE):
                    respostas_limpa.append({"opção": opcao, "valor": valor})
            elif isinstance(r, str):
                m = re.match(r"(.*?)[\.,:]?\s*\(?([0-9])\)?$", r.strip())
                if m:
                    opcao = re.sub(r"[\.,:;!?\s]+$", "", m.group(1).strip()).capitalize()
                    valor = m.group(2).strip()
                    if not re.search(r"(IF RESPONSE|GO TO|CONTINUE|OTHERWISE|BOX)", opcao, re.IGNORECASE):
                        respostas_limpa.append({"opção": opcao, "valor": valor})

        json_obj["Respostas"] = respostas_limpa
        return json_obj
    return json_obj

# Mostrar motivo da rejeição do LLM
def motivo_resposta_incompleta(resposta):
    motivos = []
    if not resposta:
        return "Resposta vazia do LLM"
    if not resposta.get("Pergunta"):
        motivos.append("Pergunta ausente")
    if not resposta.get("Respostas"):
        motivos.append("Respostas ausentes")
    else:
        valores = [r.get("valor") for r in resposta.get("Respostas") if isinstance(r, dict)]
        if "7" not in valores:
            motivos.append('Valor "7" (Refused) ausente')
    return " | ".join(motivos) if motivos else "Desconhecido"

# Conciliação entre versão original e LLM
def conciliar_estrutura(estrutura_original, resposta_llm):
    if not resposta_llm or not isinstance(resposta_llm, dict):
        return estrutura_original

    resultado = {}

    resultado["Identificador"] = resposta_llm.get("Identificador") or estrutura_original.get("Identificador")
    sec_llm = resposta_llm.get("Secção", "").strip()
    resultado["Secção"] = sec_llm if sec_llm and sec_llm != "Nenhuma" else estrutura_original.get("Secção", "Nenhuma")

    pergunta_llm = resposta_llm.get("Pergunta", "").strip()
    pergunta_ok = pergunta_llm and not re.fullmatch(r"\W*", pergunta_llm)
    resultado["Pergunta"] = pergunta_llm if pergunta_ok else estrutura_original.get("Pergunta", "")

    respostas_llm = resposta_llm.get("Respostas", [])
    respostas_orig = estrutura_original.get("Respostas", [])
    combinadas = {r["valor"]: r for r in respostas_orig if isinstance(r, dict)}
    for r in respostas_llm:
        if isinstance(r, dict) and "valor" in r:
            combinadas[r["valor"]] = r

    resultado["Respostas"] = list(combinadas.values())

    # 🔽 Inserir melhorias finais aqui antes do return 🔽

    # 1. Remover secção duplicada da pergunta
    # 1. Remover secção duplicada da pergunta (com colchetes ou sem)
    secao = resultado.get("Secção", "").strip("[]").lower()
    pergunta = resultado.get("Pergunta", "")
    pergunta_lower = pergunta.lower()
    if secao and (pergunta_lower.startswith(secao) or pergunta_lower.startswith("[" + secao)):
     resultado["Pergunta"] = re.sub(re.escape(resultado["Secção"]), "", pergunta, flags=re.IGNORECASE).strip("[]: ").strip()


    # 2. Limpar respostas (capitalizar e remover hífens)
    temp_respostas = []
    for r in resultado.get("Respostas", []):
        if isinstance(r, dict) and "opção" in r:
            r["opção"] = re.sub(r"^[-\\s]*", "", r["opção"]).capitalize()
            temp_respostas.append(r)
    resultado["Respostas"] = temp_respostas

    # 3. Forçar inclusão de "Refused" se detetado na pergunta ou secção
    valores = [r["valor"] for r in resultado["Respostas"] if isinstance(r, dict)]
    texto_concat = (resultado.get("Pergunta", "") + " " + resultado.get("Secção", "")).lower()
    if "refused" in texto_concat and "7" not in valores:
        resultado["Respostas"].append({"opção": "Refused", "valor": "7"})

    return resultado