# 1) Base comum
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.local/bin:${PATH}"
RUN apt-get update && \
    apt-get install -y --no-install-recommends bash curl dos2unix && \
    rm -rf /var/lib/apt/lists/*

# Instala o uv (rápido, sem venv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) Deps (instala uma vez)
FROM base AS deps
WORKDIR /opt
COPY requirements.txt .
# instala direto no sistema (sem venv)
# se quiser ainda mais determinismo: --no-build-isolation
RUN uv pip install --no-cache --system -r requirements.txt

# 3) API (api/ está DENTRO de app/)
FROM base AS api
WORKDIR /app
ENV PYTHONPATH=/app
# reaproveita os site-packages já instalados no estágio deps
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY ./app /app
CMD ["python", "api/server.py"]

# 4) Imagem final do Projeto (startup.sh agora em app/scripts/startup.sh)
FROM base AS projeto
WORKDIR /app
ENV PYTHONPATH=/app

COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY . .

# 👇 aplica dos2unix + chmod no caminho correto
RUN dos2unix app/scripts/startup.sh && chmod +x app/scripts/startup.sh

# podes usar caminho relativo (porque WORKDIR=/app) ou absoluto:
CMD ["bash", "/app/scripts/startup.sh"]
# (ou) CMD ["bash", "/app/scripts/startup.sh"]