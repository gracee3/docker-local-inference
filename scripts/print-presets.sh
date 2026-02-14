#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Model Presets
─────────────────────────────────────────────────────────────────────────────────
Preset Name                  Path                                           Runtime
──────────────────────────── ────────────────────────────────────────────── ────────
QWEN_14B_AWQ                 /data/models/qwen2p5-14b-instruct-awq          vLLM
QWEN_7B_AWQ                  /data/models/qwen2p5-7b-instruct-awq           vLLM
QWEN_VL_2B                   /data/models/qwen2-vl-2b-instruct              vLLM
QWEN3_VL_30B_FP8             /data/models/qwen3-vl-30b-a3b-thinking-fp8     vLLM
DEVSTRAL_SMALL_24B           /data/models/mistralai-devstral-small-2-24b-instruct-2512 vLLM
QWEN_CODER_7B_Q8             /data/models/qwen2p5-coder-7b-instruct-q8-0    llama.cpp
NOMIC_EMBED_CODE_Q6          /data/models/nomic-embed-code-q6-k             llama.cpp

Usage:
  make run-qwen3            # Qwen3 safe profile (concurrency capped via --max-num-seqs 2)
  make run-qwen3-fast       # Qwen3 high-throughput profile
  make run-qwen14           # Qwen2.5-14B single-GPU default
  make run-qwen14-sidecar   # Qwen2.5-14B on :8002 alongside Qwen3
  make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1
  make run-llama-llm PRESET=QWEN_CODER_7B_Q8 GPU=0
EOF
