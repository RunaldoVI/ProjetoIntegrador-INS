# user.py
from flask import Flask, Blueprint, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
import mysql.connector
import os
import bcrypt  # <-- Biblioteca para hashing seguro
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)

CORS(app, supports_credentials=True, origins=["http://localhost:8080"]) 

user_bp = Blueprint('user_bp', __name__)

def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'user'),
        password=os.getenv('DB_PASSWORD', 'password'),
        database=os.getenv('DB_NAME', 'projetofinal_ins')
    )

@user_bp.route('/uploads/avatars/<filename>')
def serve_avatar(filename):
    path = os.path.join(current_app.static_folder, 'uploads', 'avatars')
    return send_from_directory(path, filename)


@user_bp.route('/api/register', methods=['POST', 'OPTIONS'])
def register_user():
    if request.method == 'OPTIONS':
        return '', 200

    # 🌐 Verifica se é multipart/form-data
    is_multipart = request.content_type and request.content_type.startswith("multipart/form-data")

    if is_multipart:
        nome = request.form.get('nome')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        funcao = request.form.get('funcao', 'Estudante')
        instituicao = request.form.get('instituicao', 'Instituição não definida')

        avatar_file = request.files.get('avatar')
        avatar_filename = 'default.png'

        if avatar_file and avatar_file.filename.endswith('.png'):
            filename = secure_filename(avatar_file.filename)
            timestamp = int(time.time())
            avatar_filename = f"{timestamp}_{filename}"
            avatar_path = os.path.join(current_app.static_folder, "uploads", "avatars", avatar_filename)
            os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
            avatar_file.save(avatar_path)
    else:
        # Se não for multipart, assume JSON
        try:
            data = request.get_json()
        except:
            return jsonify({'error': 'Formato inválido'}), 415

        nome = data.get('nome')
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        funcao = data.get('funcao', 'Estudante')
        instituicao = data.get('instituicao', 'Instituição não definida')
        avatar_filename = data.get('avatar', 'default.png')

    # Validação
    if not nome or not email or not password:
        return jsonify({'error': 'Dados incompletos'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM utilizador WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({'error': 'Email já registado'}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute(
        "INSERT INTO utilizador (nome, email, password, funcao, instituicao, avatar) VALUES (%s, %s, %s, %s, %s, %s)",
        (nome, email, hashed_pw.decode('utf-8'), funcao, instituicao, avatar_filename)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'Utilizador registado com sucesso'}), 201

@user_bp.route('/api/login', methods=['POST', 'OPTIONS'])
def login_user():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Credenciais incompletas'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Buscar utilizador pelo email
    cursor.execute("SELECT * FROM utilizador WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # Verificar se existe e se a password bate certo
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'error': 'Email ou palavra-passe incorreta'}), 401

    return jsonify({
       'nome': user['nome'],
       'email': user['email'],
       'funcao': user.get('funcao', 'Estudante'),
       'instituicao': user.get('instituicao', 'Instituição não definida'),
       'avatar': user.get('avatar', 'default.png'),
       'pdfs': []
    })

@user_bp.route('/api/user/profile', methods=['GET', 'PUT', 'OPTIONS'])
def user_profile():
    if request.method == 'OPTIONS':
        return '', 200

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        email = request.args.get('email', '').strip().lower()

        if not email:
            return jsonify({'error': 'Email não fornecido'}), 400

        cursor.execute("SELECT nome, email, funcao, instituicao, avatar FROM utilizador WHERE email = %s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user:
            return jsonify({'error': 'Utilizador não encontrado'}), 404

        # Retorna os dados do usuário
        user['pdfs'] = []
        return jsonify(user)

    elif request.method == 'PUT':
        
        print(f"Conteúdo recebido: {request.form}")  # Para debug, veja o conteúdo
        data = request.form  # Use form se você estiver enviando arquivos
        email = data.get('email', '').strip().lower()
        nome = data.get('nome', '').strip()
        funcao = data.get('funcao', '').strip()
        instituicao = data.get('instituicao', '').strip()
        senha = data.get('senha', '').strip()  # Senha (opcional)
        avatar = data.get('avatar', None)  # Avatar (opcional)

        if not email or not nome:
            return jsonify({'error': 'Campos obrigatórios em falta'}), 400

        # Atualizar o perfil
        update_query = "UPDATE utilizador SET nome = %s, funcao = %s, instituicao = %s"
        update_values = [nome, funcao, instituicao]

        # Se a senha foi fornecida, fazer o hash e atualizar
        if senha:
            hashed_pw = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
            update_query += ", password = %s"
            update_values.append(hashed_pw.decode('utf-8'))

        # Se o avatar foi fornecido, atualizar
        if avatar:
            update_query += ", avatar = %s"
            update_values.append(avatar)

        update_query += " WHERE email = %s"
        update_values.append(email)

        cursor.execute(update_query, tuple(update_values))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'status': 'Perfil atualizado com sucesso'})

@user_bp.route('/api/user/upload_pdf', methods=['POST'])
def guardar_pdf_historico():
    email = request.form.get('email')
    pdf = request.files.get('pdf')

    if not email or not pdf:
        return jsonify({'error': 'Email ou ficheiro não fornecido'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Buscar ID do utilizador
        cursor.execute("SELECT id FROM utilizador WHERE email = %s", (email,))
        resultado = cursor.fetchone()
        if not resultado:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Utilizador não encontrado'}), 404

        utilizador_id = resultado[0]

        # Guardar ficheiro no sistema
        nome_pdf = secure_filename(pdf.filename)
        pasta_pdfs = os.path.join(current_app.static_folder, 'uploads', 'pdfs')
        os.makedirs(pasta_pdfs, exist_ok=True)
        caminho_pdf = os.path.join(pasta_pdfs, nome_pdf)
        pdf.save(caminho_pdf)

        # Inserir na tabela historico_pdfs
        cursor.execute(
            "INSERT INTO historico_pdfs (utilizador_id, nome_pdf, data_upload) VALUES (%s, %s, NOW())",
            (utilizador_id, nome_pdf)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'PDF guardado com sucesso'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/api/user/historico', methods=['GET'])
def obter_historico_pdfs():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email não fornecido'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
           """
           SELECT h.nome_pdf, h.data_upload
           FROM historico_pdfs h
           JOIN utilizador u ON h.utilizador_id = u.id
           WHERE u.email = %s
           ORDER BY h.data_upload DESC
           """,
           (email,)
        )
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()

        historico = [{'nome': row[0], 'data': row[1].strftime('%Y-%m-%d %H:%M')} for row in resultados]

        return jsonify({'historico': historico})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/api/pdf/todos', methods=['GET'])
def obter_todos_pdfs():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT h.nome_pdf, u.nome AS nome_utilizador,
                   DATE_FORMAT(h.data_upload, '%Y-%m-%d %H:%i') AS data
            FROM historico_pdfs h
            JOIN utilizador u ON u.id = h.utilizador_id
            ORDER BY h.data_upload DESC
        """)

        historico = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({'historico': historico})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
app.register_blueprint(user_bp)
