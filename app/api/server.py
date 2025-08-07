#server.py
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import subprocess
import os
import json
from user import user_bp

import os
app = Flask(__name__, static_url_path='/static',
            static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../Frontend/static')))


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
        modo_bruto = request.form.get("modo", "automatico")
        modo = modo_bruto.replace("--modo", "").strip()
        instrucoes_extra = request.form.get("instrucoes", "").strip()

        subprocess.run(
            ["python", "/app/Backend/ProjetoFinal.py", filepath, modo, instrucoes_extra],
             check=True
            )

        if modo == "preview":
            preview_path = "preview_output.json"
            if os.path.exists(preview_path):
                with open(preview_path, "r", encoding="utf-8") as f:
                    preview_data = json.load(f)
                return jsonify(preview_data), 200
            else:
                return jsonify({'error': 'Preview não encontrado'}), 500

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


@app.route('/download-excel', methods=['GET'])
def download_excel():
    excel_path = os.path.join(UPLOAD_FOLDER, "INS-NHANES-DPQ_J.xlsx")
    
    if os.path.exists(excel_path):
        return send_file(
            excel_path,
            as_attachment=True,
            download_name="INS-NHANES-DPQ_J.xlsx",  # nome visível no download
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        return jsonify({'error': 'Ficheiro Excel não encontrado'}), 404



# --- EXECUTAR A APP ---
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
