#!/usr/bin/env bash
set -euo pipefail

# Auto-detect .gguf file in /model directory
MODEL_FILE=$(find /model -maxdepth 1 -name '*.gguf' -type f | head -1)
if [ -z "$MODEL_FILE" ]; then
  echo "ERROR: No .gguf file found in /model/"
  ls -la /model/ 2>/dev/null || echo "/model/ does not exist"
  exit 1
fi
echo "Using model: $MODEL_FILE"
exec /app/llama-server --model "$MODEL_FILE" "$@"
