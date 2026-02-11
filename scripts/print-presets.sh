#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Model Presets
─────────────────────────────────────────────────────────────────────────────────
Preset Name                  Path                                           Runtime
──────────────────────────── ────────────────────────────────────────────── ────────
QWEN_14B_AWQ                 /data/models/Qwen/Qwen2.5-14B-Instruct-AWQ/   vLLM
QWEN_7B_AWQ                  /data/models/Qwen2.5-7B-Instruct-AWQ          vLLM
QWEN_VL_2B                   /data/models/Qwen2-VL-2B-Instruct             vLLM
QWEN3_VL_30B_FP8             /data/models/Qwen/Qwen3-VL-30B-A3B-Thinking-FP8/ vLLM
DEVSTRAL_SMALL_24B           /data/models/mistralai/Devstral-Small-2-24B-Instruct-2512/ vLLM
QWEN_CODER_7B_Q8             /data/models/Qwen2.5-Coder-7B-Instruct-Q8_0   llama.cpp
NOMIC_EMBED_CODE_Q6          /data/models/nomic-embed-code-Q6_K             llama.cpp

Usage:
  make run-qwen3            # Qwen3 safe profile (concurrency capped via --max-num-seqs 2)
  make run-qwen3-fast       # Qwen3 high-throughput profile
  make run-qwen14           # Qwen2.5-14B single-GPU default
  make run-qwen14-sidecar   # Qwen2.5-14B on :8002 alongside Qwen3
  make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1
  make run-llama-llm PRESET=QWEN_CODER_7B_Q8 GPU=0
EOF
