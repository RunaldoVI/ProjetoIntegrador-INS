#!/bin/sh
set -eu

# limpa/cria o log
: > /app/ollama-progress.log

echo '⏳ A aguardar que o Ollama esteja pronto...'
until curl -sf http://ollama:11434/ >/dev/null; do
  sleep 2
done

# lê nomes dos modelos do .env (ou usa defaults)
MODEL_CHAT="${CHAT_MODEL:-mistral}"
MODEL_EMB="${EMB_MODEL:-nomic-embed-text}"

pull_model() {
  name="$1"
  echo "✅ A puxar modelo: $name ..."
  curl -s -X POST http://ollama:11434/api/pull \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"${name}\"}" \
    | tee -a /app/ollama-progress.log
  printf "\n" >> /app/ollama-progress.log
}

# puxa chat + embeddings (evita pull duplicado se forem iguais)
pull_model "$MODEL_CHAT"
[ "$MODEL_EMB" = "$MODEL_CHAT" ] || pull_model "$MODEL_EMB"

echo '✅ Ambiente pronto. Aguardando uploads de PDF via API...'
tail -f /dev/null
