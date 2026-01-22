# docker-vllm-qwen

Minimal Docker wrapper for running [Qwen2.5-14B-Instruct-AWQ](https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct-AWQ) with [vLLM](https://github.com/vllm-project/vllm).

Model weights are **bind-mounted** from your host filesystem (not baked into the image), so you can swap models without rebuilding.

Tuned for **RTX 5000 16GB** (or similar ~16GB VRAM GPUs).

## Quick Start

```bash
# Clone the model (requires git-lfs)
git lfs install

# Option A: From ModelScope
git clone https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct-AWQ /data/models/Qwen2.5-14B-Instruct-AWQ

# Option B: From HuggingFace
#git clone https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-AWQ /data/models/Qwen2.5-14B-Instruct-AWQ

# Build and run
make setup
make build
make run-detached

# Test
make healthcheck
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "/model", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## Requirements

- Docker with NVIDIA GPU support
- ~16GB VRAM (tested on RTX 5000)
- ~10GB disk for model weights
- git-lfs for cloning the model

## Configuration

Edit variables in `Makefile` or override at runtime:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `/data/models/Qwen2.5-14B-Instruct-AWQ` | Path to model on host |
| `CACHE_PATH` | `~/.cache/vllm` | Cache directory for torch compile, HF |
| `GPU_MEM_UTIL` | `0.85` | GPU memory utilization (0.0-1.0) |
| `MAX_MODEL_LEN` | `4096` | Maximum context length |
| `PORT` | `8000` | Server port |

Override example:
```bash
make run-detached GPU_MEM_UTIL=0.88 MAX_MODEL_LEN=6144
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make setup` | Create cache directories |
| `make build` | Build Docker image |
| `make run` | Run interactively (foreground) |
| `make run-detached` | Run as daemon with auto-restart |
| `make stop` | Stop and remove container |
| `make logs` | Follow container logs |
| `make healthcheck` | Check server health |
| `make models` | List loaded models |
| `make shell` | Shell into running container |
| `make clean` | Stop container and remove image |

## Tuning for 16GB VRAM

The default settings are conservative for stability:

- `GPU_MEM_UTIL=0.85` - leaves headroom for CUDA graphs
- `MAX_MODEL_LEN=4096` - prevents OOM during warmup

**If you see OOM errors:**
- Add `--enforce-eager` to disable CUDA graphs (slower but uses less memory)
- Reduce `MAX_MODEL_LEN` further

**If stable and want more context:**
- Try `MAX_MODEL_LEN=6144` with `--enforce-eager`
- 8192 context will OOM during CUDA graph capture on 16GB

## API

The server exposes an OpenAI-compatible API:

- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `GET /v1/models` - List models
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## License

MIT
