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

def extrair_blocos_limpos(texto_pagina):
    linhas = texto_pagina.splitlines()
    blocos = []
    bloco_atual = []
    identificador_regex = re.compile(r"^[A-Z]{2,5}[-._]?\d{2,4}")

    def linha_util(l):
        return not re.match(r"^(BOX|CAPI|CHECK ITEM|INSTRUCTION|SOFT EDIT|HARD EDIT|ERROR MESSAGE|HAND ?CARD|OTHERWISE|GO TO|IF RESPONSE)", l, re.IGNORECASE)

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

def separar_pergunta_respostas(bloco, secao_geral):
    linhas = bloco.splitlines()
    identificador = ""
    pergunta = ""
    respostas = []
    secao_local = None

    id_regex = re.compile(r"^([A-Z]{2,5}[-._]?\d{2,4})")
    secao_regex = re.compile(r"\[(.*?)\]")
    resp_regex = re.compile(r"(.*?)\.*\s*\(?([0-9]{1,4})\)?(?:\s*\(.*?\))?$")

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

    # Limpar instruções residuais da pergunta
    pergunta = re.sub(r"(\u2022|\uf0b7|\uf0fc|\uf0a7|\u25aa|\u25cf|\u25cb|)", "", pergunta)
    pergunta = re.sub(r"(IF RESPONSE TO.*?|GO TO .*?|BOX \d+|CHECK ITEM.*?)$", "", pergunta, flags=re.IGNORECASE).strip()

    secao_final = secao_local if secao_local else (secao_geral.strip("[]") if secao_geral and pergunta.startswith(secao_geral) else "Nenhuma")
    if secao_geral and pergunta.startswith(secao_geral):
        pergunta = pergunta.replace(secao_geral, "").strip()

    respostas_formatadas = []
    for r in respostas:
        m = re.match(r"(.*?)[\s\.,:;!?-]*\(?([0-9]{1,4})\)?", r.strip())
        if m:
            texto = re.sub(r"[\.,:;!?\s]+$", "", m.group(1).strip()).capitalize()
            valor = m.group(2).strip()
            if texto and not re.fullmatch(r"\(?\d{1,4}\)?", texto):
                if not re.search(r"(IF RESPONSE|GO TO|CONTINUE|OTHERWISE|BOX)", texto, re.IGNORECASE):
                    respostas_formatadas.append({"opção": texto, "valor": valor})

    valores_existentes = [r["valor"] for r in respostas_formatadas]
    if any(v.endswith("9") for v in valores_existentes) and not any(v.endswith("7") for v in valores_existentes):
        texto_original = "\n".join(linhas)
        if re.search(r"\bRefused\b.*\b7\b", texto_original, re.IGNORECASE):
            respostas_formatadas.insert(-1, {"opção": "Refused", "valor": "7"})

    if not respostas_formatadas and re.search(r"(GO TO NEXT SECTION|CHECK ITEM|BOX|INSTRUCTION)", pergunta, re.IGNORECASE):
        return None

    return {
        "Identificador": identificador,
        "Secção": secao_final,
        "Pergunta": pergunta.strip(),
        "Respostas": respostas_formatadas
    }
