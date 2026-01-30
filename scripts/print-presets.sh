#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Model Presets
─────────────────────────────────────────────────────────────────────────────────
Preset Name                  Path                                           Runtime
──────────────────────────── ────────────────────────────────────────────── ────────
QWEN_14B_AWQ                 /data/models/Qwen2.5-14B-Instruct-AWQ         vLLM
QWEN_7B_AWQ                  /data/models/Qwen2.5-7B-Instruct-AWQ          vLLM
QWEN_VL_2B                   /data/models/Qwen2-VL-2B-Instruct             vLLM
QWEN_CODER_7B_Q8             /data/models/Qwen2.5-Coder-7B-Instruct-Q8_0   llama.cpp
NOMIC_EMBED_CODE_Q6          /data/models/nomic-embed-code-Q6_K             llama.cpp

Usage:
  make run-llm PRESET=QWEN_14B_AWQ GPU=0
  make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1
  make run-llama-llm PRESET=QWEN_CODER_7B_Q8 GPU=0
EOF
