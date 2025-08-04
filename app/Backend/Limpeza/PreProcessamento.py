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
    padroes = [
        r"Please press the \u201cBack\u201d button.*?(try again\.?)",
        r"ENTER (AGE|UNIT|A NUMBER|QUANTITY)",
        r"\. ?220G.*?DUQ\.220Q",
        r"\. ?[A-Z]+\-[0-9]+",
        r"HARD EDIT.*?",
        r"CAPI INSTRUCTIONS?:.*?",
        r"INSTRUCTIONS TO SP:.*?",
        r"CHECK ITEM.*?",
        r"\. ?ELSE CONTINUE\.",
        r"\s{2,}",
        r"[”“]"
    ]
    for padrao in padroes:
        texto = re.sub(padrao, "", texto, flags=re.IGNORECASE)
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

    # 🧠 Truncamento e remoção de ruído após ?
    pergunta_split = re.split(r"\?\s*", pergunta)
    if len(pergunta_split) == 1:
        pergunta = pergunta_split[0].strip()
    else:
        perguntas_validas = []
        for part in pergunta_split:
            part = part.strip()
            if not part or part in [".", ":"]:
                continue
            if re.search(r"\b(go to|otherwise|continue|select|press|enter|clear|try again|duq|dpq)[\b\s\d\-_.]*", part, re.IGNORECASE):
                break
            if re.fullmatch(r"\d+", part):
                continue
            perguntas_validas.append(part + "?")
        pergunta = " ".join(perguntas_validas).strip()

    if not pergunta or re.fullmatch(r"[^\w]+", pergunta):
        return None

    secao_final = secao_local if secao_local else (secao_geral.strip("[]") if secao_geral and pergunta.startswith(secao_geral) else "Nenhuma")
    if secao_geral and pergunta.startswith(secao_geral):
        pergunta = pergunta.replace(secao_geral, "").strip()

    # Reconstrução de respostas
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
    vistos = {}

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

            if not any("(" in l for l in linhas[1:]) and len(corpo.split()) <= 15:
                if re.match(r"^(the following questions|these questions|this section)", corpo.strip(), re.IGNORECASE):
                    nova_secao = re.sub(r"^.*?:?\s*", "", corpo.strip("_. ").capitalize())
                    secao_atual = nova_secao
                    print(f"\n🔄 Nova secção inferida (por heurística): {secao_atual}")
                    continue

            entrada = separar_pergunta_respostas(texto, secao_atual)
            if entrada:
                id_ = entrada["Identificador"]
                # 👇 Lógica para evitar duplicados com menos respostas
                if id_ in vistos:
                    anterior = vistos[id_]
                    if len(entrada["Respostas"]) > len(anterior["Respostas"]):
                        print(f"\n⚠️ Substituído duplicado com ID {id_} por versão mais completa")
                        vistos[id_] = entrada
                    else:
                        print(f"\n⚠️ Ignorado duplicado com ID {id_}")
                else:
                    vistos[id_] = entrada

    return list(vistos.values())
