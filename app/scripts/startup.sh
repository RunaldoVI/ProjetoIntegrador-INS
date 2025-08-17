#!/bin/sh
set -eu

LOG_DIR=/app/logs
LOG_FILE="$LOG_DIR/ollama-progress.log"
mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

echo '⏳ A aguardar que o Ollama esteja pronto...'
until curl -sf http://ollama:11434/ >/dev/null; do
  sleep 2
done

MODEL_CHAT="${CHAT_MODEL:-mistral}"
MODEL_EMB="${EMB_MODEL:-nomic-embed-text}"

pull_model() {
  name="$1"

  # 1) Já existe? (200 = disponível)
  http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://ollama:11434/api/show \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${name}\"}")

  if [ "$http_code" = "200" ]; then
    echo "✅ Modelo '${name}' já disponível. (skip pull)"
    return 0
  fi

  echo "⬇️  A puxar modelo: $name ..."
  # no-buffer para atualizar o log em tempo real
  stdbuf -oL -eL curl -N -sS -X POST http://ollama:11434/api/pull \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"${name}\"}" | stdbuf -oL -eL tee -a "$LOG_FILE"
  printf "\n" >> "$LOG_FILE"
  sync
}

pull_model "$MODEL_CHAT"
[ "$MODEL_EMB" = "$MODEL_CHAT" ] || pull_model "$MODEL_EMB"

###############################################################################
# 🚀 QDRANT: esperar, verificar coleção e ingerir só se precisar
###############################################################################
QDRANT_URL="${QDRANT_URL:-http://qdrant:6333}"
QDRANT_COLLECTION="${QDRANT_COLLECTION:-user_kb}"    # muda se quiseres
INGEST_TARGETS="${INGEST_TARGETS:-perguntas,respostas,repo,userkb}"
INGEST_BATCH="${INGEST_BATCH:-64}"

echo "⏳ A aguardar que o Qdrant esteja pronto em $QDRANT_URL ..."
until curl -sf "$QDRANT_URL/ready" >/dev/null 2>&1 || curl -sf "$QDRANT_URL/collections" >/dev/null 2>&1; do
  sleep 2
done

needs_ingest=0
if ! curl -sf "$QDRANT_URL/collections/$QDRANT_COLLECTION" >/dev/null 2>&1; then
  echo "ℹ️  Coleção '$QDRANT_COLLECTION' ainda não existe."
  needs_ingest=1
else
  COUNT=$(curl -s -X POST "$QDRANT_URL/collections/$QDRANT_COLLECTION/points/count" \
    -H "Content-Type: application/json" -d '{"exact":true}' | sed -n 's/.*"count":\([0-9]\+\).*/\1/p')
  if [ -z "$COUNT" ] || [ "$COUNT" = "0" ]; then
    echo "ℹ️  Coleção '$QDRANT_COLLECTION' existe mas está vazia."
    needs_ingest=1
  else
    echo "✅ Qdrant já indexado: $COUNT pontos na coleção '$QDRANT_COLLECTION'."
  fi
fi

if [ "$needs_ingest" -eq 1 ]; then
  echo "🚧 A iniciar ingestão para '$QDRANT_COLLECTION' (targets=$INGEST_TARGETS, batch=$INGEST_BATCH)..."
  PYTHONPATH=/app python -m Backend.Chatbot.qdrant_index \
    --targets "$INGEST_TARGETS" --batch "$INGEST_BATCH" || {
      echo "❌ Falha na ingestão inicial. Vai arrancar mesmo assim."
    }
  echo "✅ Ingestão inicial concluída."
fi

echo '✅ Ambiente pronto. Aguardando uploads de PDF via API...'
tail -f /dev/null
