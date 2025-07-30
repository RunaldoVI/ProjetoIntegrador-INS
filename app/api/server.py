#server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import subprocess
import os
import json
from user import user_bp

app = Flask(__name__)

# CORS permissivo para desenvolvimento
CORS(app)

app.register_blueprint(user_bp)

UPLOAD_FOLDER = '/app/pdfs-excels'
USERS_FILE = '/app/users.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- UPLOAD DE PDF ---

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_pdf():
    if request.method == 'OPTIONS':
        return '', 200

    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de ficheiro inválido'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        subprocess.run(["python", "/app/Backend/ProjetoFinal.py", filepath], check=True)
        return jsonify({'status': 'Processamento concluído com sucesso'}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Erro ao processar PDF: {str(e)}'}), 500

# --- MONITORAMENTO DO LLM ---

@app.route('/llm-status', methods=['GET'])
def llm_status():
    try:
        response = requests.post("http://ollama:11434/api/show", json={"model": "mistral"}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pronto = "modelfile" in data
            return jsonify({"ready": pronto})
        else:
            return jsonify({"ready": False, "error": "Erro na resposta do Ollama"})
    except Exception as e:
        return jsonify({"ready": False, "error": str(e)})

@app.route('/llm-progress', methods=['GET'])
def llm_progress():
    try:
        with open("/app/ollama-progress.log", "r") as f:
            lines = f.readlines()

        completed = total = 0
        for line in reversed(lines):
            if '"completed":' in line and '"total":' in line:
                data = json.loads(line.strip())
                completed = int(data["completed"])
                total = int(data["total"])
                break

        if total == 0:
            return jsonify({"progress": 0})
        percent = round(100 * completed / total, 2)
        return jsonify({"progress": percent})

    except Exception as e:
        return jsonify({"progress": 0, "error": str(e)})

# --- EXECUTAR A APP ---

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
