FROM python:3.11-slim

WORKDIR /app

COPY . .

# Adiciona PYTHONPATH para que "app" seja reconhecido como módulo
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y curl && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "app/ProjetoFinal.py"]