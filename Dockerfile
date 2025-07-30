FROM python:3.11-slim

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -y bash curl dos2unix && \
    pip install --no-cache-dir -r requirements.txt


# Garante que a versão de startup.sh com LF seja copiada
COPY startup.sh startup.sh
RUN dos2unix startup.sh && chmod +x startup.sh

CMD ["bash", "startup.sh"]
