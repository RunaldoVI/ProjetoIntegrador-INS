import pdfplumber, re, unicodedata, os, pandas as pd, numpy as np

# ==== carregar modelo + funções já existentes =============================
from modelo import preprocess, sent_to_vec, clf    # usa o teu módulo

ANSWER_KEYS = [
    "NOT AT ALL", "SEVERAL DAYS", "MORE THAN HALF THE DAYS",
    "NEARLY EVERY DAY", "DON'T KNOW", "DON’T KNOW", "REFUSED",
]

def linha_normal(l):
    l = unicodedata.normalize("NFKD", l).encode("ascii","ignore").decode()
    l = re.sub(r"[’‘´`]", "'", l)
    return " ".join(l.split())                     # colapsa espaços

def heuristica_resposta(l):
    up = l.upper()
    if any(k in up for k in ANSWER_KEYS):
        return True
    if re.search(r"\b0\s*1\s*2\s*3\b", up):        # p.ex. “0 1 2 3”
        return True
    # linha muito curta e não tem “?” nem ponto final
    return len(l) < 40 and "?" not in l
# --------------------------------------------------------------------------
def processar_pdf(pdf_path):
    corpus, label = [], []
    with pdfplumber.open(pdf_path) as pdf:
        buffer = ""                                # acumula partes da pergunta
        for page in pdf.pages:
            for raw in page.extract_text().splitlines():
                l = linha_normal(raw)
                if not l: 
                    continue

                # se é claramente resposta (heurística)
                if heuristica_resposta(l):
                    corpus.append(l); label.append(1)
                    continue

                # se é fim de pergunta (tem “?”)  OU começa por “n.”   
                if l.endswith("?") or re.match(r"^\d+\.", l):
                    if buffer:                     # guarda pergunta anterior
                        corpus.append(buffer.strip()); label.append(0)
                    buffer = l                     # começa nova
                else:
                    buffer += " " + l              # continua mesma pergunta

        if buffer:
            corpus.append(buffer.strip()); label.append(0)

    # fallback: usa modelo para linhas ambíguas (ex.: sem “?” nem n.)
    for i, texto in enumerate(corpus):
        if label[i] == 0 and "?" not in texto and not re.match(r"^\d+\.", texto):
            vec = sent_to_vec(preprocess(texto)).reshape(1,-1)
            label[i] = int(clf.predict(vec)[0])    # 0 ou 1
    return corpus, label
# --------------------------------------------------------------------------
def processar_pasta(pasta):
    all_text, all_lab = [], []
    for file in os.listdir(pasta):
        if file.lower().endswith(".pdf"):
            print("🔄  A processar:", file)
            c, l = processar_pdf(os.path.join(pasta, file))
            all_text.extend(c);  all_lab.extend(l)
    return all_text, all_lab
# --------------------------------------------------------------------------
if __name__ == "__main__":
    textos, labels = processar_pasta("_
