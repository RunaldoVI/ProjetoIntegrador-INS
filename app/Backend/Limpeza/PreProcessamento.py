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

def classificar_bloco_tipo(bloco):
    texto = bloco.lower()
    if texto.strip().startswith("box") or "check item" in texto:
        return "Outro"
    if "?" not in texto and "please select" not in texto and not any(op in texto for op in ["1", "2", "7", "9"]):
        return "Secção"
    return "Pergunta"

def limpar_instrucao_tecnica(texto):
    # Remover campos visuais tipo ___| 
    texto = re.sub(r"\|_+\|", "", texto)

    # Instruções específicas do NHANES
    texto = re.sub(r"___\|?\s*ENTER\s+(AGE|NUMBER|UNIT|A NUMBER|VALUE).*?(\.|\”|\"|,|and)?", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"(Clear[,\.]?|“Clear,” and|Please\s*,?\s*”?\s*and)", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"press the [“\"]?back[”\"]? button.*?clear.*?", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"try again[\.”\"\']?", "", texto, flags=re.IGNORECASE)

    # Instruções genéricas
    texto = re.sub(r"please (enter|select)[^\.]{0,80}(\.|”|\"|$)", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"your response (must|cannot).*?(\.|$)", "", texto, flags=re.IGNORECASE)

    # Instruções condicionais
    texto = re.sub(r"IF\s+SP\s+.*?(?=\.|”|\"|\Z)", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"CONTINUE WITH DUQ\.\d{3}", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"GO TO DUQ\.\d{3}", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bDUQ[-–_.]?\d{1,4}\b", "", texto)

    # Outros
    texto = re.sub(r"(INSTRUCTIONS TO SP.*?)(?=\.|”|\"|\Z)", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bG/Q/U\b", "", texto)
    texto = re.sub(r"(\u2022|\uf0b7|\uf0fc|\uf0a7|\u25aa|\u25cf|\u25cb|)", "", texto)
    texto = re.sub(r"\s{2,}", " ", texto)
    texto = re.sub(r"[”,\"']+\s*$", "", texto)

    return texto.strip()

def extrair_blocos_limpos(texto_pagina):
    linhas = texto_pagina.splitlines()
    blocos = []
    bloco_atual = []
    identificador_regex = re.compile(r"^[A-Z]{2,5}[-._]?\d{2,4}")

    def linha_util(l):
        return not re.match(
            r"^(BOX|CAPI|CHECK ITEM|INSTRUCTION|SOFT EDIT|HARD EDIT|ERROR MESSAGE|HAND ?CARD|OTHERWISE|GO TO|IF RESPONSE)",
            l, re.IGNORECASE)

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

    blocos_dict = []
    for b in blocos:
        blocos_dict.append({
            "texto": b,
            "tipo": classificar_bloco_tipo(b)
        })
    return blocos_dict

def separar_pergunta_respostas(bloco, secao_geral):
    linhas = bloco.splitlines()
    identificador = ""
    pergunta = ""
    respostas = []
    secao_local = None

    id_regex = re.compile(r"^([A-Z]{2,5}[-._]?\d{2,4})")
    secao_regex = re.compile(r"\[(.*?)\]")
    resp_regex = re.compile(r"^(.*?)(?:[\.\s]{3,})\(?([0-9]{1,4})\)?(?:\s*\(.*?\))?$")

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

    pergunta = limpar_instrucao_tecnica(pergunta)

    secao_final = secao_local if secao_local else (secao_geral.strip("[]") if secao_geral and pergunta.startswith(secao_geral) else "Nenhuma")
    if secao_geral and pergunta.startswith(secao_geral):
        pergunta = pergunta.replace(secao_geral, "").strip()

    respostas_reconstruidas = []
    buffer = ""
    for r in respostas:
        r_clean = r.strip()
        if re.match(r"^\(?\d{1,4}\)?$", r_clean) or len(r_clean.split()) <= 2:
            buffer += " " + r_clean
        else:
            if buffer:
                r = buffer + " " + r_clean
                buffer = ""
            respostas_reconstruidas.append(r.strip())
    if buffer:
        respostas_reconstruidas.append(buffer.strip())

    respostas_formatadas = []
    for r in respostas_reconstruidas:
        m = resp_regex.match(r.strip())
        if m:
            texto = re.sub(r"[\.,:;!?\s]+$", "", m.group(1).strip()).capitalize()
            valor = m.group(2).strip()
            if texto and not re.fullmatch(r"\(?\d{1,4}\)?", texto) and len(texto) > 2:
                if not re.search(r"^(target|duq|dpq)$", texto, re.IGNORECASE):
                    respostas_formatadas.append({"opção": texto, "valor": valor})

    valores = [r["valor"] for r in respostas_formatadas]
    if "2" not in valores and re.search(r"\bno\b.*?2\b", bloco, re.IGNORECASE):
        respostas_formatadas.append({"opção": "No", "valor": "2"})
    if any(v.endswith("9") for v in valores) and not any(v.endswith("7") for v in valores):
        if re.search(r"\bRefused\b.*\b7\b", bloco, re.IGNORECASE):
            respostas_formatadas.insert(-1, {"opção": "Refused", "valor": "7"})

    if (not respostas_formatadas and len(pergunta.split()) <= 4) or re.fullmatch(r"^(OTHERWISE|CHECK ITEM|BOX).*", pergunta, re.IGNORECASE):
        return None

    return {
        "Identificador": identificador,
        "Secção": secao_final,
        "Pergunta": pergunta.strip(),
        "Respostas": respostas_formatadas
    }

def processar_blocos_com_seccoes(blocos_dict, secao_mais_comum=None):
    resultado = []
    secao_atual = secao_mais_comum

    for bloco in blocos_dict:
        tipo = bloco["tipo"]
        texto = bloco["texto"]

        if tipo == "Secção":
            secao_atual = texto.strip()
            print(f"\n🔄 Nova secção propagada: {secao_atual}")
            continue

        if tipo == "Pergunta":
            linhas = texto.splitlines()
            corpo = " ".join(linhas[1:]).lower()

            # Heurística: introduções que deviam ser secção
            if not any("(" in l for l in linhas[1:]) and len(corpo.split()) <= 15:
                if re.match(r"^(the following questions|these questions|this section)", corpo.strip(), re.IGNORECASE):
                    nova_secao = re.sub(r"^.*?:?\s*", "", corpo.strip("_. ").capitalize())
                    secao_atual = nova_secao
                    print(f"\n🔄 Nova secção inferida (por heurística): {secao_atual}")
                    continue

            entrada = separar_pergunta_respostas(texto, secao_atual)
            if entrada:
                resultado.append(entrada)

    return resultado
