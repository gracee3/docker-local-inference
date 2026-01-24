# docker-vllm-qwen

Minimal Docker wrapper for running Qwen family models with [vLLM](https://github.com/vllm-project/vllm).

Supports both **text** and **vision** models. Model weights are **bind-mounted** from your host filesystem (not baked into the image), so you can swap models without rebuilding.

Tuned for **RTX 5000 16GB** (or similar ~16GB VRAM GPUs).

## Supported Models

| Model | Type | Notes |
|-------|------|-------|
| Qwen2.5-14B-Instruct-AWQ | Text | Default text model (AWQ quantized) |
| Qwen2.5-7B-Instruct-AWQ | Text | Smaller text variant |
| Qwen2-VL-7B-Instruct-AWQ | Vision | Larger multimodal model (text + images) |
| Qwen2-VL-2B-Instruct | Vision | Smaller multimodal model (text + images) |

## Quick Start

```bash
# Clone a model (requires git-lfs)
git lfs install

# Text models
git clone https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-AWQ /data/models/Qwen2.5-14B-Instruct-AWQ
git clone https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ /data/models/Qwen2.5-7B-Instruct-AWQ

# Vision models
git clone https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct-AWQ /data/models/Qwen2-VL-7B-Instruct-AWQ
git clone https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct /data/models/Qwen2-VL-2B-Instruct

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

## Running the Vision Model

To run a vision model instead of the default text model:

```bash
make run-vision VISION_MODEL=/data/models/Qwen2-VL-7B-Instruct-AWQ
make run-vision VISION_MODEL=/data/models/Qwen2-VL-2B-Instruct MAX_MODEL_LEN=4096
```

Or start manually:

```bash
docker run -d \
  --name vllm-vision \
  --gpus all \
  --ipc=host \
  -p 8000:8000 \
  -v /data/models/Qwen2-VL-2B-Instruct:/model:ro \
  -v ~/.cache/vllm:/cache \
  local/vllm-qwen:0.11.0 \
  --model /model \
  --host 0.0.0.0 --port 8000 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 4096
```

### Testing Vision

```bash
# Install dependencies
pip install httpx

# Run vision test script
python3 test_vision.py                    # Basic health check
python3 test_vision.py /path/to/image.jpg # Test with an image
```

Example vision API call:

```bash
# Base64 encode an image and send to the API
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/model",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<BASE64_IMAGE>"}},
        {"type": "text", "text": "What is in this image?"}
      ]
    }],
    "max_tokens": 200
  }'
```

## Requirements

- Docker with NVIDIA GPU support
- Sufficient VRAM for the model you choose (quantized models require less)
- git-lfs for cloning models

## Configuration

Edit variables in `Makefile` or override at runtime:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `/data/models/Qwen2.5-14B-Instruct-AWQ` | Path to model on host |
| `VISION_MODEL` | `/data/models/Qwen2-VL-7B-Instruct-AWQ` | Vision model path for `make run-vision` |
| `CACHE_PATH` | `~/.cache/vllm` | Cache directory for torch compile |
| `GPU_MEM_UTIL` | `0.85` | GPU memory utilization (0.0-1.0) |
| `MAX_MODEL_LEN` | `8192` | Maximum context length |
| `PORT` | `8000` | Server port |

Override examples:
```bash
make run-detached MODEL_PATH=/data/models/Qwen2-VL-2B-Instruct MAX_MODEL_LEN=4096
make run-vision VISION_MODEL=/data/models/Qwen2-VL-2B-Instruct MAX_MODEL_LEN=4096
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
- 8192 context may OOM during CUDA graph capture on 16GB

## API

The server exposes an OpenAI-compatible API:

- `POST /v1/chat/completions` - Chat completions (text and vision)
- `POST /v1/completions` - Text completions
- `GET /v1/models` - List models
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## License

MIT
