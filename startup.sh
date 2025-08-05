#!/bin/bash

rm -rf /app/ollama-progress.log
touch /app/ollama-progress.log

echo '⏳ A aguardar que o Ollama esteja pronto...'
until curl -s http://ollama:11434/; do
  sleep 2
done

echo '✅ Ollama ativo. A puxar modelo mistral...'

curl -s -X POST http://ollama:11434/api/pull \
  -H 'Content-Type: application/json' \
  -d '{"name": "qwen:7b"}' \
  | tee /app/ollama-progress.log

echo '✅ Ambiente pronto. Aguardando uploads de PDF via API...'
tail -f /dev/null
