from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

UPLOAD_FOLDER = '/app/pdfs-excels'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome de ficheiro inválido'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Chama o ProjetoFinal.py com o novo ficheiro
    try:
        subprocess.run(["python", "/app/Backend/ProjetoFinal.py", filepath], check=True)
        return jsonify({'status': 'Processamento concluído com sucesso'}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Erro ao processar PDF: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')