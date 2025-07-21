FROM python:3.11

# Cria e define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto para o container
COPY app/ /app

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando padrão ao iniciar o container
CMD ["python", "ProjetoFinal.py"]
