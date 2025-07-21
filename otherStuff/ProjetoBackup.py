import pdfplumber
import os
import requests
import json
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import LabelEncoder
import pandas as pd
from collections import Counter
import re

# 1. Função para extrair texto do PDF e guardar num .txt
def extrair_texto_para_txt(caminho_pdf):
    # Cria pasta "PDF_Extraido" se não existir
    pasta_saida = "PDF_Extraido"
    os.makedirs(pasta_saida, exist_ok=True)

    # Define nome base e caminho final
    nome_base = os.path.splitext(os.path.basename(caminho_pdf))[0]
    caminho_txt = os.path.join(pasta_saida, f"{nome_base}_extraido.txt")

    # Extrai o texto por página e guarda no ficheiro
    with pdfplumber.open(caminho_pdf) as pdf, open(caminho_txt, "w", encoding="utf-8") as f_out:
        for i, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text()
            if texto and texto.strip():
                f_out.write(f"===== Página {i} =====\n\n")
                f_out.write(texto + "\n\n")

    return caminho_txt

# 2. Caminho para o PDF a extrair
caminho_pdf = "Alcohol_Use.pdf"  # Altera aqui se necessário

# 3. Extrai o texto e guarda no .txt
caminho_txt = extrair_texto_para_txt(caminho_pdf)
print(f"✅ Texto extraído para {caminho_txt}")

# 4. Lê o ficheiro .txt e separa por páginas
with open(caminho_txt, "r", encoding="utf-8") as f:
    conteudo = f.read()

# 5. Separa o conteúdo em páginas com base no separador "===== Página N ====="
paginas = conteudo.split("===== Página")
paginas = [p.strip() for p in paginas if p.strip()]

# 6. Pergunta ao modelo e ao LLM
pergunta = (
    "Consegues fazer uma lista organizada com os identificadores, as perguntas e as suas opções de resposta "
    "que aparecem neste questionário?\n\n"
    "❗ Instruções importantes:\n"
    "- Não traduzas nada.\n"
    "- Se houver algum texto introdutório ou enunciado que se aplica a várias perguntas seguidas (por exemplo, uma frase geral antes de uma lista de perguntas), considera esse texto como uma **Secção** comum.\n"
    "- Se não houver um enunciado comum, coloca 'Secção: Nenhuma'.\n"
    "- **Ignora blocos que sejam apenas instruções, anotações ou encaminhamentos** (ex: 'BOX 2', 'GO TO', 'CHECK ITEM', etc).\n"
    "- **Ignora qualquer pergunta que não tenha pelo menos uma opção de resposta com valor numérico associado** (ex: '(0)', '(1)', '(2)'...).\n"
    "- Usa exatamente o seguinte formato:\n\n"
    "Identificador: [código]\n"
    "Secção: [texto da secção ou 'Nenhuma']\n"
    "Pergunta: [texto completo da pergunta]\n"
    "Respostas:\n"
    "  - [opção 1] (valor)\n"
    "  - [opção 2] (valor)\n"
    "  - ...\n\n"
    "Consegues colocar tudo num formato JSON estruturado?\n"
)

# 7. Payload para a API do Ollama
for i, texto_pagina in enumerate(paginas, start=1):
    if len(texto_pagina.strip()) < 20:
        print(f"\n📄 Página {i} ignorada (sem conteúdo significativo).")
        continue

    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": "Estás a interpretar uma página de um questionário clínico. Responde apenas com base nesta página."},
            {"role": "user", "content": f"{texto_pagina}\n\n{pergunta}"}
        ]
    }

    url = "http://localhost:11434/api/chat"
    response = requests.post(url, json=payload, stream=True)

    if response.status_code == 200:
        print("🧠 Resposta:")
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        print(data["message"]["content"], end="")
                except json.JSONDecodeError:
                    print(f"\n⚠️ Erro a processar linha: {line}")
        print("\n" + "-" * 50)
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.text)

        input("\n✅ Execução concluída. Pressiona Enter para sair...")

