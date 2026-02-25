# docker-local-inference

Local inference stack for running downloaded models in `/data/models` with a lightweight local backend.

This repo is centered on `vLLM` with `make run-llm PRESET=...` workflows.

## Requirements

- Docker
- At least one model downloaded under `/data/models`
- Optional: CUDA-capable GPU

## Quick setup

```bash
make build
cp backend/.env.example backend/.env
cd backend && cargo run
```

## vLLM: available `make run-llm PRESET=...`

The following presets resolve to model folders in this machine’s `/data/models`.

```bash
# default small-model runs below use GPU1
make run-llm PRESET=QWEN_14B_AWQ GPU=all
make run-llm PRESET=QWEN_7B_AWQ GPU=1
make run-llm PRESET=QWEN_VL_2B GPU=1
make run-llm PRESET=QWEN2_VL_7B_AWQ GPU=1
make run-llm PRESET=QWEN3_VL_30B_FP8 GPU=all
make run-llm PRESET=DEVSTRAL_SMALL_24B GPU=all
make run-llm PRESET=DEEPSEEK_R1_QWEN_32B GPU=all
make run-llm PRESET=PHI3P5_MINI_INSTRUCT GPU=1
make run-llm PRESET=QWEN2P5_INSTRUCT_1P5B GPU=1
make run-llm PRESET=QWEN3_32B_AWQ GPU=all
make run-llm PRESET=QWEN3_CODER_30B_A3B_INSTRUCT GPU=all
```

Preset-aware helpers:

```bash
make run-qwen3            # uses QWEN3_VL_30B_FP8 (safe profile)
make run-qwen3-fast       # uses QWEN3_VL_30B_FP8 (higher throughput profile)
make run-qwen14           # uses QWEN_14B_AWQ
make run-qwen14-balanced  # uses QWEN_14B_AWQ
make run-vision           # uses PRESET=QWEN3_VL_30B_FP8 on all GPUs
```

Common commands:

```bash
make presets
make healthcheck-llm
make logs-llm
make stop-llm
make stop-all
```

You can always set a custom path directly:

```bash
make run-llm MODEL_PATH=/data/models/<your-model-folder> GPU=1
```

## llama.cpp (optional, keep for later use)

The llama.cpp path is used for GGUF and embedding-style models.

```bash
make build-llama
make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1
make run-llama-llm PRESET=QWEN_CODER_7B_Q8 GPU=1
```

Useful checks for llama containers:

```bash
make healthcheck-embed
make logs-embed
make stop-embed
```

## Backend

- API base: `http://127.0.0.1:3000`
- Useful endpoint: `POST /llm/chat`

## Persistence

- Model paths: `/data/models/...`
- Backend DB: `backend/data/app.db` (`sqlite://data/app.db` from `backend/`)

## License

MIT
