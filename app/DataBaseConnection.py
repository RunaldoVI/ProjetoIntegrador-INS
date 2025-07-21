import mysql.connector
import json

# 1. Ligação à base de dados
def conectar_bd():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="projetofinal_ins"
    )

# 2. Função para inserir dados do JSON na base de dados
def importar_json_para_bd(caminho_json):
    conn = conectar_bd()
    cursor = conn.cursor()

    with open(caminho_json, "r", encoding="utf-8") as f:
        dados = json.load(f)

    for entrada in dados:
        identificador = entrada["identificador"]
        secao = entrada.get("secao", "Nenhuma")
        pergunta = entrada["pergunta"]
        respostas = entrada["respostas"]

        # Inserir identificador (ou obter id se já existir)
        cursor.execute("SELECT id FROM identificadores WHERE codigo = %s", (identificador,))
        resultado = cursor.fetchone()
        if resultado:
            identificador_id = resultado[0]
        else:
            cursor.execute("INSERT INTO identificadores (codigo) VALUES (%s)", (identificador,))
            identificador_id = cursor.lastrowid

        # Inserir pergunta
        cursor.execute("INSERT INTO perguntas (texto, identificador_id) VALUES (%s, %s)", (pergunta, identificador_id))
        pergunta_id = cursor.lastrowid

        for resp in respostas:
            texto = resp["texto"]
            valor = resp["valor"]

            # Verifica se resposta já existe
            cursor.execute("SELECT id FROM respostas WHERE texto = %s AND identificador_id = %s", (texto, identificador_id))
            resposta_resultado = cursor.fetchone()
            if resposta_resultado:
                resposta_id = resposta_resultado[0]
            else:
                cursor.execute("INSERT INTO respostas (texto, identificador_id) VALUES (%s, %s)", (texto, identificador_id))
                resposta_id = cursor.lastrowid

            # Associar pergunta <-> resposta
            cursor.execute("INSERT IGNORE INTO pergunta_resposta (pergunta_id, resposta_id) VALUES (%s, %s)", (pergunta_id, resposta_id))

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Dados importados com sucesso para a base de dados.")
