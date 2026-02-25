# Local model paths and Makefile mapping (`/data/models`)

This file maps the models currently present in `/data/models` to the repository’s supported Makefile presets/paths.

## Makefile presets currently configured

| Preset | `Makefile` path | Present in `/data/models` | Runtime target |
|---|---|---|---|
| `QWEN_14B_AWQ` | `/data/models/qwen2p5-14b-instruct-awq` | ✅ | `make run-llm PRESET=QWEN_14B_AWQ GPU=0` |
| `QWEN_7B_AWQ` | `/data/models/qwen2p5-7b-instruct-awq` | ✅ | `make run-llm PRESET=QWEN_7B_AWQ GPU=0` |
| `QWEN_VL_2B` | `/data/models/qwen2-vl-2b-instruct` | ✅ | `make run-llm PRESET=QWEN_VL_2B GPU=0` |
| `QWEN_CODER_7B_Q8` | `/data/models/qwen2p5-coder-7b-instruct-q8-0` | ✅ | `make run-llama-llm PRESET=QWEN_CODER_7B_Q8 GPU=0` |
| `NOMIC_EMBED_CODE_Q6` | `/data/models/nomic-embed-code-q6-k` | ✅ | `make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1` |
| `QWEN3_VL_30B_FP8` | `/data/models/qwen3-vl-30b-a3b-thinking-fp8` | ✅ | `make run-qwen3` |
| `DEVSTRAL_SMALL_24B` | `/data/models/mistralai-devstral-small-2-24b-instruct-2512` | ✅ | `make run-llm PRESET=DEVSTRAL_SMALL_24B GPU=0` |
| `QWEN2_VL_7B_AWQ` | `/data/models/qwen2-vl-7b-instruct-awq` | ✅ | `make run-llm PRESET=QWEN2_VL_7B_AWQ GPU=0` |
| `DEEPSEEK_R1_QWEN_32B` | `/data/models/deepseek-r1-distill-qwen-32b` | ✅ | `make run-llm PRESET=DEEPSEEK_R1_QWEN_32B GPU=0` |
| `PHI3P5_MINI_INSTRUCT` | `/data/models/phi3p5-mini-instruct` | ✅ | `make run-llm PRESET=PHI3P5_MINI_INSTRUCT GPU=0` |
| `QWEN2P5_INSTRUCT_1P5B` | `/data/models/qwen2p5-instruct-1p5b` | ✅ | `make run-llm PRESET=QWEN2P5_INSTRUCT_1P5B GPU=0` |
| `QWEN3_32B_AWQ` | `/data/models/qwen3-32b-awq` | ✅ | `make run-llm PRESET=QWEN3_32B_AWQ GPU=0` |
| `QWEN3_CODER_30B_A3B_INSTRUCT` | `/data/models/qwen3-coder-30b-a3b-instruct` | ✅ | `make run-llm PRESET=QWEN3_CODER_30B_A3B_INSTRUCT GPU=0` |
| `VISION_MODEL` (run-vision) | `/data/models/qwen3-vl-30b-a3b-thinking-fp8` | ✅ | `make run-vision` |

## Other downloaded entries in `/data/models` not currently mapped to a preset

- `awq.log`
- `gguf`
- `baai-bge-reranker-large`
- `qwen2p5-1p5b-instruct-gguf` (empty directory; verify model files are fully downloaded)
- `riva`

If you want them as first-class targets, add new preset variables and optional aliases in `Makefile` and `scripts/print-presets.sh`.

## Quick compatibility summary

- All preset paths defined in `Makefile` and `scripts/print-presets.sh` currently point to existing directories in `/data/models`.
- The default `MODEL_PATH` points to an existing local model.
- No Makefile preset paths are missing from `/data/models` today.
