from flask import Flask, render_template, request, jsonify
from TextExtractorPDF import extrair_texto_para_txt
from PromptLLM import enviar_pagina_para_llm
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.pdf'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # Processar PDF
        caminho_txt = extrair_texto_para_txt(filepath)
        with open(caminho_txt, "r", encoding="utf-8") as f:
            conteudo = f.read()

        paginas = [p.strip() for p in conteudo.split("----- Página") if p.strip()]
        resultados = [enviar_pagina_para_llm(p) for p in paginas]

        return jsonify({'resultados': resultados})
    return jsonify({'erro': 'Ficheiro inválido'}), 400

@app.route('/limpar', methods=['POST'])
def limpar():
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    return jsonify({'mensagem': 'Ficheiros limpos com sucesso'})
