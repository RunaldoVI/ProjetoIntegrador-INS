# user.py
from flask import Blueprint, request, jsonify
import mysql.connector
import os
import bcrypt  # <-- Biblioteca para hashing seguro

user_bp = Blueprint('user_bp', __name__)

def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'user'),
        password=os.getenv('DB_PASSWORD', 'password'),
        database=os.getenv('DB_NAME', 'projetofinal_ins')
    )

@user_bp.route('/api/register', methods=['POST', 'OPTIONS'])
def register_user():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json
    nome = data.get('nome')
    email = data.get('email', '').strip().lower()
    password = data.get('password')
    funcao = data.get('funcao', 'Estudante')
    instituicao = data.get('instituicao', 'Instituição não definida')
    avatar = data.get('avatar', 'default.png')  # ADICIONADO

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
        (nome, email, hashed_pw.decode('utf-8'), funcao, instituicao, avatar)
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

        # PDF histórico (exemplo futuro — aqui está vazio)
        user['pdfs'] = []
        return jsonify(user)

    elif request.method == 'PUT':
        data = request.json
        email = data.get('email', '').strip().lower()
        nome = data.get('nome', '').strip()
        funcao = data.get('funcao', '').strip()
        instituicao = data.get('instituicao', '').strip()

        if not email or not nome:
            return jsonify({'error': 'Campos obrigatórios em falta'}), 400

        cursor.execute(
            "UPDATE utilizador SET nome = %s, funcao = %s, instituicao = %s WHERE email = %s",
            (nome, funcao, instituicao, email)
        )
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'status': 'Perfil atualizado com sucesso'})