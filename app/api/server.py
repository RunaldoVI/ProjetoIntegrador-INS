#server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import subprocess
import os
import json

app = Flask(__name__)

# CORS permissivo para desenvolvimento
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

UPLOAD_FOLDER = '/app/pdfs-excels'
USERS_FILE = '/app/users.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Resposta para preflight (OPTIONS)
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response

# Utilitários
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# --- API DE AUTENTICAÇÃO ---

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register_user():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    nome = data.get('nome')
    email = data.get('email')
    password = data.get('password')
    funcao = data.get('funcao', 'Estudante')
    instituicao = data.get('instituicao', 'Instituição não definida')

    if not nome or not email or not password:
        return jsonify({'error': 'Dados incompletos'}), 400

    users = load_users()
    if any(u['email'] == email for u in users):
        return jsonify({'error': 'Email já registado'}), 409

    new_user = {
        'nome': nome,
        'email': email,
        'password': password,
        'funcao': funcao,
        'instituicao': instituicao,
        'pdfs': []
    }

    users.append(new_user)
    save_users(users)
    return jsonify({'status': 'Utilizador registado com sucesso'}), 201

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login_user():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Credenciais incompletas'}), 400

    users = load_users()
    user = next((u for u in users if u['email'] == email), None)

    if not user or user['password'] != password:
        return jsonify({'error': 'Email ou palavra-passe incorreta'}), 401

    return jsonify({
        'nome': user['nome'],
        'email': user['email'],
        'funcao': user.get('funcao'),
        'instituicao': user.get('instituicao'),
        'pdfs': user.get('pdfs', [])
    })

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    data = request.get_json()
    email = data.get('email')
    nome = data.get('nome')
    funcao = data.get('funcao')
    instituicao = data.get('instituicao')

    if not email:
        return jsonify({'error': 'Email obrigatório'}), 400

    users = load_users()
    user = next((u for u in users if u['email'] == email), None)
    if not user:
        return jsonify({'error': 'Utilizador não encontrado'}), 404

    user['nome'] = nome or user['nome']
    user['funcao'] = funcao or user.get('funcao', '')
    user['instituicao'] = instituicao or user.get('instituicao', '')

    save_users(users)
    return jsonify({'status': 'Perfil atualizado com sucesso'}), 200



@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email não fornecido'}), 400

    users = load_users()
    user = next((u for u in users if u['email'] == email), None)
    if not user:
        return jsonify({'error': 'Utilizador não encontrado'}), 404

    profile = {
        'nome': user['nome'],
        'email': user['email'],
        'funcao': user.get('funcao', 'Estudante'),
        'instituicao': user.get('instituicao', 'Instituição'),
        'pdfs': user.get('pdfs', [])
    }
    return jsonify(profile)



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
