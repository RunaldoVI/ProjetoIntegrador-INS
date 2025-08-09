import re
import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FICHEIRO_INPUT = os.path.join(BASE_DIR, '..', 'PDF_Extraido', 'DPQ_J_estruturado.txt')
FICHEIRO_OUTPUT = os.path.join(BASE_DIR, '..', 'PDF_Extraido', 'DPQ_J.json')

# === Função auxiliar para identificar a frase mais repetida ===
def identificar_secao_mais_comum(texto):
    linhas = texto.splitlines()
    linhas_filtradas = [
        linha.strip()
        for linha in linhas
        if linha.strip() and len(linha.strip()) > 20  # evitar lixo pequeno
    ]
    contagem = Counter(linhas_filtradas)
    frase_mais_comum, _ = contagem.most_common(1)[0]
    return frase_mais_comum

# === Função principal ===
def processar_txt_para_json(caminho_txt, caminho_json):
    with open(caminho_txt, 'r', encoding='utf-8') as f:
        texto = f.read()

    # === DETETAR A SECÇÃO MAIS REPETIDA ===
    secao_global = identificar_secao_mais_comum(texto)
    print(f"➡️ Secção mais comum detetada: \"{secao_global}\"")

    blocos = re.split(r'\[Página \d+\] - ', texto)

    resultados = []

    for bloco in blocos:
        if not bloco.strip():
            continue

        # Identificador (ex: DPQ.010)
        match_id = re.match(r'(DPQ\.\d{3})', bloco)
        if not match_id:
            continue  # Ignorar blocos sem identificador

        identificador = match_id.group(1)

        # Remover instruções técnicas e linhas irrelevantes
        linhas = bloco.splitlines()
        linhas_limpa = [linha.strip() for linha in linhas if linha.strip() and not re.match(r'(?i)(HANDCARD|CAPI|CHECK ITEM|HELP SCREEN|READ|PROBE|DISPLAY|CODE ALL|SOFT EDIT|HARD EDIT)', linha)]

        # Separar pergunta e respostas
        conteudo_pergunta = []
        respostas = []

        for i, linha in enumerate(linhas_limpa):
            if re.search(r'\.\.\.\s*\d+$', linha):  # resposta com número no fim
                respostas = linhas_limpa[i:]
                break
            else:
                conteudo_pergunta.append(linha)

        # Remover secao_global se estiver no início da pergunta
        pergunta_junta = ' '.join(conteudo_pergunta).strip()
        if pergunta_junta.startswith(secao_global):
            pergunta_limpa = pergunta_junta[len(secao_global):].strip()
        else:
            pergunta_limpa = pergunta_junta

        # Processar respostas
        lista_respostas = []
        for resp in respostas:
            m = re.match(r'(.+?)\.\.\.\.*\s*(\d+)$', resp)
            if m:
                opcao = m.group(1).strip().rstrip(',')
                valor = m.group(2)
                lista_respostas.append({"opção": opcao, "valor": valor})

        resultado = {
            "Identificador": identificador,
            "Secção": secao_global,
            "Pergunta": pergunta_limpa,
            "Respostas": lista_respostas
        }
        resultados.append(resultado)

    # Escrever JSON final
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"✅ Ficheiro JSON gerado: {caminho_json} com {len(resultados)} blocos")

# === EXECUÇÃO ===
if __name__ == '__main__':
    processar_txt_para_json(FICHEIRO_INPUT, FICHEIRO_OUTPUT)
