# docker-local-inference

Minimal Docker wrapper for running local LLM and embedding models with [vLLM](https://github.com/vllm-project/vllm) and [llama.cpp](https://github.com/ggml-org/llama.cpp).

Model weights are **bind-mounted** from your host filesystem (`/data/models/...`) -- not baked into images. Swap models without rebuilding.

## Supported Runtimes

| Runtime | Use Case | Model Formats | Image |
|---------|----------|---------------|-------|
| vLLM | LLM inference (chat/completions) | HF (FP16, AWQ, GPTQ) | `local/vllm-qwen:0.11.0` |
| llama.cpp | LLM inference or embeddings | GGUF only | `local/llama-server:latest` |

**vLLM cannot load GGUF/GGML models.** Use llama.cpp for GGUF quantizations (Q4, Q6, Q8, etc.).

## Supported Models

| Preset | Model | Format | Runtime | VRAM |
|--------|-------|--------|---------|------|
| `QWEN_14B_AWQ` | Qwen2.5-14B-Instruct-AWQ | AWQ | vLLM | ~14 GB |
| `QWEN_7B_AWQ` | Qwen2.5-7B-Instruct-AWQ | AWQ | vLLM | ~7 GB |
| `QWEN_VL_2B` | Qwen2-VL-2B-Instruct | FP16 | vLLM | ~4 GB |
| `QWEN_CODER_7B_Q8` | Qwen2.5-Coder-7B-Instruct-Q8_0 | GGUF Q8 | llama.cpp | ~16 GB |
| `NOMIC_EMBED_CODE_Q6` | nomic-embed-code-Q6_K | GGUF Q6 | llama.cpp | ~1 GB |

List all presets: `make presets`

## Quick Start

```bash
# Build images
make build           # vLLM image
make build-llama     # llama.cpp image

# Download an HF model
./scripts/get-hf-model.sh Qwen/Qwen2.5-14B-Instruct-AWQ

# Run with defaults (vLLM, Qwen2.5-14B-AWQ, all GPUs, port 8000)
make setup
make run-llm

# Test
make healthcheck-llm
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "/model", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## GPU Pinning

Control which GPU a container uses with the `GPU` variable:

```bash
make run-llm GPU=0           # LLM on GPU 0
make run-embed GPU=1         # Embeddings on GPU 1
make run-llm GPU=all         # All GPUs (default)
```

Requires NVIDIA Container Toolkit. Uses `--gpus "device=N"` under the hood.

## Dual-GPU Setup (2x RTX 3090)

Run LLM on GPU 0 and embeddings on GPU 1 simultaneously:

```bash
# Build both images
make build
make build-llama

# GPU 0: vLLM for chat completions (port 8000)
make run-llm PRESET=QWEN_14B_AWQ GPU=0

# GPU 1: llama.cpp for embeddings (port 8001)
make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1

# Test both
make healthcheck-llm
make healthcheck-embed

# Embeddings test
curl http://localhost:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "def hello(): pass"}'
```

Or use Docker Compose (GPU pinning hardcoded to device 0 and 1 in `compose.yml`):

```bash
docker compose up -d        # Start both services
docker compose up -d llm    # Start only LLM
docker compose up -d embed  # Start only embeddings
docker compose down         # Stop all
```

## Downloading Models

### HF Models (for vLLM)

```bash
# Using the helper script (git-lfs required)
./scripts/get-hf-model.sh Qwen/Qwen2.5-14B-Instruct-AWQ
./scripts/get-hf-model.sh Qwen/Qwen2.5-7B-Instruct-AWQ
./scripts/get-hf-model.sh Qwen/Qwen2-VL-2B-Instruct
```

### GGUF Models (for llama.cpp)

GGUF files are single files. Download them from Hugging Face and place them in a directory under `/data/models/`:

```bash
# nomic-embed-code Q6_K
mkdir -p /data/models/nomic-embed-code-Q6_K
# Download from: https://huggingface.co/nomic-ai/nomic-embed-code-GGUF
# Place the .gguf file in /data/models/nomic-embed-code-Q6_K/

# Qwen2.5-Coder-7B Q8_0
mkdir -p /data/models/Qwen2.5-Coder-7B-Instruct-Q8_0
# Download from: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF
# Place the .gguf file in /data/models/Qwen2.5-Coder-7B-Instruct-Q8_0/
```

Each GGUF model directory should contain exactly one `.gguf` file. The entrypoint auto-detects it.

## Running GGUF Chat Models

To run a GGUF-format chat model (e.g., Qwen2.5-Coder-7B Q8_0) under llama.cpp:

```bash
make run-llama-llm PRESET=QWEN_CODER_7B_Q8 GPU=0 LLAMA_PORT=8000

# Test
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-coder", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## Running the Vision Model

```bash
make run-vision
# Or override the model:
make run-vision VISION_MODEL=/data/models/Qwen2-VL-2B-Instruct

# Test with the vision test script
pip install httpx
python3 test_vision.py                    # Basic health check
python3 test_vision.py /path/to/image.jpg # Test with an image
```

## Requirements

- Docker with NVIDIA GPU support (NVIDIA Container Toolkit)
- git-lfs for cloning HF models
- Sufficient VRAM (see Supported Models table)

## Configuration

Override variables at runtime or edit in `Makefile`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU` | `all` | GPU device: `0`, `1`, or `all` |
| `PRESET` | *(none)* | Model preset name (see `make presets`) |
| `MODEL_PATH` | `/data/models/Qwen2.5-14B-Instruct-AWQ` | Path to model directory on host |
| `CACHE_PATH` | `~/.cache/vllm` | Cache directory for vLLM |
| `GPU_MEM_UTIL` | `0.85` | vLLM GPU memory utilization (0.0-1.0) |
| `MAX_MODEL_LEN` | `8192` | vLLM maximum context length |
| `PORT` | `8000` | vLLM server port |
| `LLAMA_PORT` | `8001` | llama.cpp server port |
| `LLAMA_N_GPU_LAYERS` | `999` | Layers to offload to GPU (999 = all) |
| `LLAMA_CTX_SIZE` | `8192` | llama.cpp context size |
| `LLAMA_POOLING` | `last` | Pooling type for embeddings |

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make setup` | Create cache directories |
| `make build` | Build vLLM Docker image |
| `make build-llama` | Build llama.cpp Docker image |
| `make run` | Run vLLM interactively (foreground) |
| `make run-detached` | Run vLLM as daemon |
| `make run-llm` | Run vLLM LLM server (detached) |
| `make run-embed` | Run llama.cpp embedding server (detached) |
| `make run-llama-llm` | Run llama.cpp chat server (detached) |
| `make run-vision` | Run vLLM vision model (detached) |
| `make stop` / `make stop-all` | Stop containers |
| `make stop-llm` / `make stop-embed` | Stop specific service |
| `make logs` / `make logs-llm` / `make logs-embed` | Follow logs |
| `make healthcheck-llm` | Check vLLM health |
| `make healthcheck-embed` | Check llama.cpp health |
| `make models` | List loaded vLLM models |
| `make presets` | List available model presets |
| `make shell` | Shell into running container |
| `make clean` / `make clean-all` | Remove containers and images |

## Tuning

### vLLM (AWQ/GPTQ models)

- `GPU_MEM_UTIL=0.85` leaves headroom for CUDA graphs
- If OOM: add `--enforce-eager` (use `run-experimental`) or reduce `MAX_MODEL_LEN`
- RTX 3090 24GB can comfortably run 14B AWQ at `MAX_MODEL_LEN=16384`

### llama.cpp (GGUF models)

- `LLAMA_N_GPU_LAYERS=999` offloads all layers to GPU. Reduce if OOM.
- `LLAMA_CTX_SIZE` controls context window. Reduce if OOM.
- No `--gpu-memory-utilization` equivalent; OOM manifests as CUDA malloc failure.

## Notes on nomic-embed-code

- Requires `--pooling last` (set by default via `LLAMA_POOLING`)
- Queries should be prefixed with: `"Represent this query for searching relevant code:"`
- This is an application-layer concern -- the embedding server returns raw vectors regardless of prefix.

## API

Both runtimes expose OpenAI-compatible APIs:

**vLLM (port 8000)**
- `POST /v1/chat/completions` - Chat completions
- `POST /v1/completions` - Text completions
- `GET /v1/models` - List models
- `GET /health` - Health check

**llama.cpp (port 8001)**
- `POST /v1/chat/completions` - Chat completions (when running chat model)
- `POST /v1/embeddings` - Embeddings (when running with `--embedding`)
- `GET /health` - Health check

## License

MIT
