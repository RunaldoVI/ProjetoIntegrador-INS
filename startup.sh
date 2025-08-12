#!/bin/sh
set -eu

# limpa/cria o log do pull do Ollama
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
    -d "{\"name\":\"${name}\"}" | tee -a /app/ollama-progress.log
  printf "\n" >> /app/ollama-progress.log
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
  PYTHONPATH=/app python Backend/Chatbot/qdrant_index.py \
    --targets "$INGEST_TARGETS" --batch "$INGEST_BATCH" || {
      echo "❌ Falha na ingestão inicial. Vai arrancar mesmo assim."; 
    }
  echo "✅ Ingestão inicial concluída."
fi

echo '✅ Ambiente pronto. Aguardando uploads de PDF via API...'
tail -f /dev/null
