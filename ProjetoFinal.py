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
caminho_pdf = "DPQ_J.pdf"  # Altera aqui se necessário

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
    "❗ Importante:\n"
    "- Não traduzas nada.\n"
    "- Usa o seguinte formato exato:\n\n"
    "Identificador: [código]\n"
    "Pergunta: [texto completo]\n"
    "Respostas:\n"
    "  - [opção 1] (valor)\n"
    "  - [opção 2] (valor)\n"
    "  - ...\n\n"
    "Consegues me colocar tudo num formato json?\n"
)

# Carregar o CSV
df = pd.read_csv("training_data.csv")
df = df.dropna(subset=["texto", "label"])
df["label"] = df["label"].astype(str).str.strip()
df = df[df["label"] != ""]
X = df["texto"].astype(str)
y = df["label"]

# Codificação dos rótulos
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
contagem = Counter(y_encoded)
indices_validos = [i for i, label in enumerate(y_encoded) if contagem[label] > 1]
X = X.iloc[indices_validos]
y_encoded = y_encoded[indices_validos]

# Separar em treino e teste
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

# Gerar embeddings com MiniLM
embedder = SentenceTransformer("all-MiniLM-L6-v2")
X_train_embed = embedder.encode(X_train.tolist(), show_progress_bar=True)
X_test_embed = embedder.encode(X_test.tolist(), show_progress_bar=True)

# Treinar classificador
clf = LogisticRegression(max_iter=1000)
clf.fit(X_train_embed, y_train)

# Avaliar
y_pred = clf.predict(X_test_embed)
labels_utilizadas = sorted(set(y_encoded))
nomes_utilizados = label_encoder.inverse_transform(labels_utilizadas)
print(classification_report(y_test, y_pred, labels=labels_utilizadas, target_names=nomes_utilizados.astype(str), zero_division=0))

# Funções de agrupamento e divisão
def agrupar_blocos_genericos(linhas):
    blocos = []
    bloco_atual = []
    for linha in linhas:
        if re.match(r"^[A-Z]{2,4}\.\d{3}", linha.strip()):
            if bloco_atual:
                blocos.append(" ".join(bloco_atual))
                bloco_atual = []
        bloco_atual.append(linha.strip())
    if bloco_atual:
        blocos.append(" ".join(bloco_atual))
    return blocos

def dividir_blocos_em_subblocos(bloco):
    subblocos = []
    partes = re.split(r"\n{2,}|(?<=[:?.])\s{2,}", bloco)
    for parte in partes:
        linha = parte.strip()
        if len(linha) >= 30:
            subblocos.append(linha)
    return subblocos

# ➤ MINI-LM: Classificação por sub-blocos
pagina_1 = paginas[0]
linhas = [linha.strip() for linha in pagina_1.splitlines() if linha.strip()]
blocos = agrupar_blocos_genericos(linhas)

subblocos_todos = []
for bloco in blocos:
    subblocos = dividir_blocos_em_subblocos(bloco)
    subblocos_todos.extend(subblocos)

subblocos_embed = embedder.encode(subblocos_todos)
preds_sub = clf.predict(subblocos_embed)
labels_sub = label_encoder.inverse_transform(preds_sub)

print("\n📄 [MiniLM] Classificação por sub-blocos (mais precisos) da Página 1:\n")
for label, sub in zip(labels_sub, subblocos_todos):
    print(f"\n[{label}]\n{sub}\n{'-'*60}")

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
