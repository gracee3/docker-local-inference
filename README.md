# docker-local-inference

Local inference stack for running downloaded models in `/data/models` with `make run-llm PRESET=...` workflows.

This repo wraps:
- vLLM runtime (`make run-llm`)
- llama.cpp runtime (`make run-embed`, `make run-llama-llm`)
- Open WebUI (`make run-openwebui`)

## Requirements

- Docker
- At least one model downloaded under `/data/models`
- Optional: CUDA-capable GPU

## Quick setup

```bash
make build
make build-llama
```

## vLLM: available `make run-llm PRESET=...`

The following presets resolve to model folders in this machine’s `/data/models`.

```bash
# default small-model runs below use GPU1
make run-llm PRESET=QWEN_14B_AWQ GPU=all
make run-llm PRESET=QWEN_7B_AWQ GPU=1
make run-llm PRESET=QWEN_VL_2B GPU=1
make run-llm PRESET=QWEN2_VL_7B_AWQ GPU=1
make run-llm PRESET=QWEN3_32B_AWQ GPU=all
make run-llm PRESET=DEVSTRAL_SMALL_24B GPU=all
make run-llm PRESET=DEEPSEEK_R1_QWEN_32B GPU=all
make run-llm PRESET=PHI3P5_MINI_INSTRUCT GPU=1
make run-llm PRESET=QWEN2P5_INSTRUCT_1P5B GPU=1
make run-llm PRESET=QWEN3_32B_AWQ GPU=all
make run-llm PRESET=QWEN3_CODER_30B_A3B_INSTRUCT GPU=all
```

Preset-aware helpers:

```bash
make run-qwen7b           # default fast chat/instruct profile (no-eager, single GPU)
make run-qwen3            # uses QWEN3_32B_AWQ (safe profile)
make run-qwen3-fast       # uses QWEN3_32B_AWQ (higher throughput profile)
make run-qwen14           # uses QWEN_14B_AWQ
make run-qwen14-balanced  # uses QWEN_14B_AWQ
make run-vision           # uses PRESET=QWEN3_VL_30B_FP8 on all GPUs
make run-devstral-small-24b # high-context, single-user tuned (64k)
make run-devstral-small-24b-fast # safer 32k profile
make run-openwebui         # starts Open WebUI on port 3002 and points to vLLM at vllm-qwen:8000/v1
```

Common commands:

```bash
make presets
make healthcheck-llm
make logs-llm
make logs-openwebui
make stop-llm
make stop-openwebui
make stop-all
make healthcheck-openwebui
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

## Open WebUI (chat frontend)

Run a local chat frontend against the vLLM server:

```bash
make run-openwebui
make run-openwebui-with-llm
make open-openwebui
make healthcheck-openwebui
make logs-openwebui
make stop-openwebui
```

Open WebUI defaults:
- Web UI: `http://localhost:3002`
- Backend API target: `http://vllm-qwen:8000/v1` (container DNS on shared network)
- Data directory: `~/.local/share/open-webui` (mounted into container at `/app/backend/data`)
- You can open it from make with: `make open-openwebui`
- If you start Open WebUI without `run-llm`, ensure both containers share `DOCKER_NETWORK`:
  - `DOCKER_NETWORK=local-inference-net`

Useful checks for llama containers:

```bash
make healthcheck-embed
make logs-embed
make stop-embed
```

## License

MIT
