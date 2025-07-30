#!/bin/sh

echo '⏳ A aguardar que o Ollama esteja pronto...'
until curl -s http://ollama:11434/; do
  sleep 2
done

echo '✅ Ollama ativo. A puxar modelo mistral...'
curl -s -X POST http://ollama:11434/api/pull -H 'Content-Type: application/json' -d '{"name": "mistral"}'

echo '✅ Ambiente pronto. Aguardando uploads de PDF via API...'
tail -f /dev/null  # Mantém o container ativo sem correr o script
