# Local LLM / Embedding Server
# Supports vLLM (AWQ/GPTQ/FP16) and llama.cpp (GGUF)
# Tuned for dual-GPU setup (e.g. 2× RTX 3090 24GB)

# ── Images ──────────────────────────────────────────────
IMAGE_NAME   := local/vllm-qwen
IMAGE_TAG    := 0.11.0
IMAGE        := $(IMAGE_NAME):$(IMAGE_TAG)

LLAMA_IMAGE_NAME := local/llama-server
LLAMA_IMAGE_TAG  := latest
LLAMA_IMAGE      := $(LLAMA_IMAGE_NAME):$(LLAMA_IMAGE_TAG)

# ── GPU pinning ─────────────────────────────────────────
# GPU=0, GPU=1, or GPU=all (default)
GPU := all

ifeq ($(GPU),all)
  GPU_FLAG := --gpus all
else
  GPU_FLAG := --gpus '"device=$(GPU)"'
endif

# ── Model presets ───────────────────────────────────────
# Usage: make run-llm PRESET=QWEN_14B_AWQ GPU=0
#        make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1

PRESET_QWEN_14B_AWQ         := /data/models/Qwen/Qwen2.5-14B-Instruct-AWQ/
PRESET_QWEN_7B_AWQ          := /data/models/Qwen2.5-7B-Instruct-AWQ
PRESET_QWEN_VL_2B           := /data/models/Qwen2-VL-2B-Instruct
PRESET_QWEN_CODER_7B_Q8     := /data/models/Qwen2.5-Coder-7B-Instruct-Q8_0
PRESET_NOMIC_EMBED_CODE_Q6  := /data/models/nomic-embed-code-Q6_K
PRESET_QWEN3_VL_30B_FP8     := /data/models/Qwen/Qwen3-VL-30B-A3B-Thinking-FP8/
PRESET_DEVSTRAL_SMALL_24B   := /data/models/mistralai/Devstral-Small-2-24B-Instruct-2512/

# Resolve PRESET → MODEL_PATH if set
ifdef PRESET
  MODEL_PATH := $(PRESET_$(PRESET))
  ifeq ($(MODEL_PATH),)
    $(error Unknown preset: $(PRESET). Run "make presets" to list available presets.)
  endif
endif

# ── Paths (defaults if no PRESET) ──────────────────────
MODEL_PATH   ?= /data/models/Qwen/Qwen2.5-14B-Instruct-AWQ/
CACHE_PATH   := $(HOME)/.cache/vllm

# ── vLLM settings ──────────────────────────────────────
# Note: 8192 context may OOM on warmup with 16GB VRAM; 4096 is stable
GPU_MEM_UTIL := 0.85
MAX_MODEL_LEN := 8192
TP_SIZE      := 1
PORT         := 8000
EXTRA_ARGS   :=

# ── llama.cpp settings ─────────────────────────────────
LLAMA_PORT         := 8001
LLAMA_N_GPU_LAYERS := 999
LLAMA_CTX_SIZE     := 8192
LLAMA_POOLING      := last

# ── Container names ────────────────────────────────────
CONTAINER_NAME := vllm-qwen
LLM_CONTAINER ?= vllm-qwen
CONTAINERS     := vllm-qwen vllm-small vllm-vision llama-llm llama-embed
SMALL_PORT     ?= 8002

# Vision model configuration
# VISION_MODEL := /data/models/Qwen2-VL-7B-Instruct-AWQ
VISION_MODEL := /data/models/Qwen/Qwen3-VL-30B-A3B-Thinking-FP8/

# Tuning notes (RTX 5000 16GB / RTX 3090 24GB):
#   Default (stable): GPU_MEM_UTIL=0.85, MAX_MODEL_LEN=4096
#   If OOM: try --enforce-eager to disable CUDA graphs
#   Experimental: GPU_MEM_UTIL=0.88, MAX_MODEL_LEN=6144 (may OOM on warmup)

.PHONY: setup build build-llama \
	run run-detached run-vision run-experimental run-llm run-embed run-llama-llm run-qwen3 run-qwen3-fast run-qwen14 run-qwen14-sidecar \
	stop stop-all stop-llm stop-embed stop-llama-llm stop-small \
	logs logs-llm logs-embed logs-small \
	healthcheck healthcheck-llm healthcheck-embed healthcheck-small \
	models shell clean clean-all presets

# ── Setup / Build ───────────────────────────────────────

setup:
	mkdir -p $(CACHE_PATH)

build:
	docker build -t $(IMAGE) .

build-llama:
	docker build -t $(LLAMA_IMAGE) -f Dockerfile.llamacpp .

# ── Run: vLLM (legacy targets, backwards-compatible) ───

run: stop-all
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		$(GPU_FLAG) \
		--ipc=host \
		-p $(PORT):8000 \
		-v $(MODEL_PATH):/model:ro \
		-v $(CACHE_PATH):/cache \
		$(IMAGE) \
		--model /model \
		--host 0.0.0.0 --port 8000 \
		--gpu-memory-utilization $(GPU_MEM_UTIL) \
		--max-model-len $(MAX_MODEL_LEN) \
		--enable-prefix-caching

run-detached: stop-all
	docker run -d \
		--name $(CONTAINER_NAME) \
		$(GPU_FLAG) \
		--ipc=host \
		-p $(PORT):8000 \
		-v $(MODEL_PATH):/model:ro \
		-v $(CACHE_PATH):/cache \
		--restart unless-stopped \
		$(IMAGE) \
		--model /model \
		--host 0.0.0.0 --port 8000 \
		--gpu-memory-utilization $(GPU_MEM_UTIL) \
		--max-model-len $(MAX_MODEL_LEN) \
		--enable-prefix-caching

run-vision: stop-all
	docker run -d \
		--name vllm-vision \
		$(GPU_FLAG) \
		--ipc=host \
		-p $(PORT):8000 \
		-v $(VISION_MODEL):/model:ro \
		-v $(CACHE_PATH):/cache \
		--restart unless-stopped \
		$(IMAGE) \
		--model /model \
		--host 0.0.0.0 --port 8000 \
		--gpu-memory-utilization $(GPU_MEM_UTIL) \
		--max-model-len 4096 \
		--enable-prefix-caching

run-experimental: stop-all
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		$(GPU_FLAG) \
		--ipc=host \
		-p $(PORT):8000 \
		-v $(MODEL_PATH):/model:ro \
		-v $(CACHE_PATH):/cache \
		$(IMAGE) \
		--model /model \
		--host 0.0.0.0 --port 8000 \
		--gpu-memory-utilization 0.88 \
		--max-model-len 6144 \
		--enable-prefix-caching \
		--enforce-eager

# ── Run: vLLM LLM server (new target) ──────────────────

run-llm: stop-llm
	docker run -d \
		--name $(LLM_CONTAINER) \
		$(GPU_FLAG) \
		--ipc=host \
		-p $(PORT):8000 \
		-v $(MODEL_PATH):/model:ro \
		-v $(CACHE_PATH):/cache \
		--restart unless-stopped \
		$(IMAGE) \
		--model /model \
		--host 0.0.0.0 --port 8000 \
		--gpu-memory-utilization $(GPU_MEM_UTIL) \
		--max-model-len $(MAX_MODEL_LEN) \
		--tensor-parallel-size $(TP_SIZE) \
		--enable-prefix-caching \
		$(EXTRA_ARGS)

# Qwen3-VL 30B FP8 (safety-first profile on 2 GPUs)
# Example:
#   make run-qwen3
#   make run-qwen3 GPU=0 TP_SIZE=1
run-qwen3:
	$(MAKE) run-llm PRESET=QWEN3_VL_30B_FP8 GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.80 MAX_MODEL_LEN=4096 EXTRA_ARGS="--max-num-seqs 2"

# Qwen3-VL 30B FP8 (higher-throughput profile, lower headroom)
run-qwen3-fast:
	$(MAKE) run-llm PRESET=QWEN3_VL_30B_FP8 GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.85 MAX_MODEL_LEN=4096

# Qwen2.5-14B-AWQ on a single GPU for smaller tasks
run-qwen14:
	$(MAKE) run-llm PRESET=QWEN_14B_AWQ GPU=0 TP_SIZE=1 GPU_MEM_UTIL=0.80 MAX_MODEL_LEN=8192

# Optional sidecar small model on a separate port so it can run alongside Qwen3
run-qwen14-sidecar: stop-small
	docker run -d \
		--name vllm-small \
		--gpus '"device=0"' \
		--ipc=host \
		-p $(SMALL_PORT):8000 \
		-v $(PRESET_QWEN_14B_AWQ):/model:ro \
		-v $(CACHE_PATH):/cache \
		--restart unless-stopped \
		$(IMAGE) \
		--model /model \
		--host 0.0.0.0 --port 8000 \
		--gpu-memory-utilization 0.75 \
		--max-model-len 4096 \
		--tensor-parallel-size 1 \
		--enable-prefix-caching

# ── Run: llama.cpp embedding server ────────────────────

run-embed: stop-embed
	docker run -d \
		--name llama-embed \
		$(GPU_FLAG) \
		-p $(LLAMA_PORT):8080 \
		-v $(MODEL_PATH):/model:ro \
		--restart unless-stopped \
		$(LLAMA_IMAGE) \
		--host 0.0.0.0 --port 8080 \
		--n-gpu-layers $(LLAMA_N_GPU_LAYERS) \
		--ctx-size $(LLAMA_CTX_SIZE) \
		--embedding \
		--pooling $(LLAMA_POOLING)

# ── Run: llama.cpp LLM server (for GGUF chat models) ──

run-llama-llm: stop-llama-llm
	docker run -d \
		--name llama-llm \
		$(GPU_FLAG) \
		-p $(LLAMA_PORT):8080 \
		-v $(MODEL_PATH):/model:ro \
		--restart unless-stopped \
		$(LLAMA_IMAGE) \
		--host 0.0.0.0 --port 8080 \
		--n-gpu-layers $(LLAMA_N_GPU_LAYERS) \
		--ctx-size $(LLAMA_CTX_SIZE)

# ── Stop ────────────────────────────────────────────────

stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

stop-all:
	@for c in $(CONTAINERS); do \
		docker stop $$c 2>/dev/null || true; \
		docker rm $$c 2>/dev/null || true; \
	done
	@echo "All containers stopped"

stop-llm:
	docker stop $(LLM_CONTAINER) 2>/dev/null || true
	docker rm $(LLM_CONTAINER) 2>/dev/null || true

stop-embed:
	docker stop llama-embed 2>/dev/null || true
	docker rm llama-embed 2>/dev/null || true

stop-llama-llm:
	docker stop llama-llm 2>/dev/null || true
	docker rm llama-llm 2>/dev/null || true

stop-small:
	docker stop vllm-small 2>/dev/null || true
	docker rm vllm-small 2>/dev/null || true

# ── Logs ────────────────────────────────────────────────

logs:
	@for c in $(CONTAINERS); do \
		if docker ps --format '{{.Names}}' | grep -q "^$$c$$"; then \
			docker logs -f $$c; \
			exit 0; \
		fi; \
	done; \
	echo "No running container found"

logs-llm:
	docker logs -f $(LLM_CONTAINER)

logs-embed:
	docker logs -f llama-embed

logs-small:
	docker logs -f vllm-small

# ── Healthcheck ─────────────────────────────────────────

healthcheck:
	@curl -sf http://localhost:$(PORT)/health && echo "healthy" || echo "unhealthy"

healthcheck-llm:
	@curl -sf http://localhost:$(PORT)/health && echo "healthy" || echo "unhealthy"

healthcheck-embed:
	@curl -sf http://localhost:$(LLAMA_PORT)/health && echo "healthy" || echo "unhealthy"

healthcheck-small:
	@curl -sf http://localhost:$(SMALL_PORT)/health && echo "healthy" || echo "unhealthy"

# ── Utility ─────────────────────────────────────────────

models:
	@curl -s http://localhost:$(PORT)/v1/models | python3 -m json.tool

shell:
	@for c in $(CONTAINERS); do \
		if docker ps --format '{{.Names}}' | grep -q "^$$c$$"; then \
			docker exec -it $$c /bin/bash; \
			exit 0; \
		fi; \
	done; \
	echo "No running container found"

presets:
	@./scripts/print-presets.sh

# ── Clean ───────────────────────────────────────────────

clean: stop
	docker rmi $(IMAGE) || true

clean-all: stop-all
	docker rmi $(IMAGE) || true
	docker rmi $(LLAMA_IMAGE) || true
