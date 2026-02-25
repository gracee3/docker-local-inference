# Local LLM / Embedding Server
# Supports vLLM (AWQ/GPTQ/FP16) and llama.cpp (GGUF)
# Tuned for dual-GPU setup (e.g. 2× RTX 3090 24GB), with small models defaulting to GPU1

# ── Images ──────────────────────────────────────────────
IMAGE_NAME   := local/vllm-qwen
IMAGE_TAG    := 0.11.0
IMAGE        := $(IMAGE_NAME):$(IMAGE_TAG)

LLAMA_IMAGE_NAME := local/llama-server
LLAMA_IMAGE_TAG  := latest
LLAMA_IMAGE      := $(LLAMA_IMAGE_NAME):$(LLAMA_IMAGE_TAG)

OPEN_WEBUI_IMAGE_NAME := ghcr.io/open-webui/open-webui
OPEN_WEBUI_IMAGE_TAG  := main
OPEN_WEBUI_IMAGE      := $(OPEN_WEBUI_IMAGE_NAME):$(OPEN_WEBUI_IMAGE_TAG)

# ── GPU pinning ─────────────────────────────────────────
# GPU=0, GPU=1, or GPU=all (default: 1)
GPU := 1

ifeq ($(GPU),all)
  GPU_FLAG := --gpus all
else
  GPU_FLAG := --gpus '"device=$(GPU)"'
endif

# ── Model presets ───────────────────────────────────────
# Usage: make run-llm PRESET=QWEN_14B_AWQ GPU=all
#        make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1

PRESET_QWEN_14B_AWQ         := /data/models/qwen2p5-14b-instruct-awq
PRESET_QWEN_7B_AWQ          := /data/models/qwen2p5-7b-instruct-awq
PRESET_QWEN_VL_2B           := /data/models/qwen2-vl-2b-instruct
PRESET_QWEN2_VL_7B_AWQ      := /data/models/qwen2-vl-7b-instruct-awq
PRESET_QWEN_CODER_7B_Q8     := /data/models/qwen2p5-coder-7b-instruct-q8-0
PRESET_NOMIC_EMBED_CODE_Q6  := /data/models/nomic-embed-code-q6-k
PRESET_QWEN3_VL_30B_FP8     := /data/models/qwen3-vl-30b-a3b-thinking-fp8
PRESET_DEVSTRAL_SMALL_24B   := /data/models/mistralai-devstral-small-2-24b-instruct-2512
PRESET_DEEPSEEK_R1_QWEN_32B := /data/models/deepseek-r1-distill-qwen-32b
PRESET_PHI3P5_MINI_INSTRUCT := /data/models/phi3p5-mini-instruct
PRESET_QWEN2P5_INSTRUCT_1P5B := /data/models/qwen2p5-instruct-1p5b
PRESET_QWEN3_32B_AWQ       := /data/models/qwen3-32b-awq
PRESET_QWEN3_CODER_30B_A3B_INSTRUCT := /data/models/qwen3-coder-30b-a3b-instruct

# Resolve PRESET → MODEL_PATH if set
ifdef PRESET
  MODEL_PATH := $(PRESET_$(PRESET))
  ifeq ($(MODEL_PATH),)
    $(error Unknown preset: $(PRESET). Run "make presets" to list available presets.)
  endif
  ifeq ($(PRESET),DEVSTRAL_SMALL_24B)
    IMAGE := vllm/vllm-openai:v0.12.0
  endif
endif

# ── Paths (defaults if no PRESET) ──────────────────────
MODEL_PATH   ?= /data/models/qwen2p5-14b-instruct-awq
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

# ── Open WebUI settings ───────────────────────────────
OPEN_WEBUI_PORT := 3002
OPEN_WEBUI_DATA := $(HOME)/.local/share/open-webui
OPEN_WEBUI_HOST_ADDR := vllm-qwen
OPEN_WEBUI_VLLM_BASE_URL := http://$(OPEN_WEBUI_HOST_ADDR):$(PORT)/v1
OPEN_WEBUI_VLLM_API_KEY := local
OPEN_WEBUI_PRESET ?= QWEN_7B_AWQ
OPEN_WEBUI_GPU ?= 1
DOCKER_NETWORK ?= local-inference-net

# ── Container names ────────────────────────────────────
CONTAINER_NAME := vllm-qwen
LLM_CONTAINER ?= vllm-qwen
OPEN_WEBUI_CONTAINER ?= open-webui
CONTAINERS     := vllm-qwen llama-llm llama-embed open-webui

# Tuning notes (RTX 5000 16GB / RTX 3090 24GB):
#   Default (stable): GPU_MEM_UTIL=0.85, MAX_MODEL_LEN=4096
#   If OOM: try --enforce-eager to disable CUDA graphs
#   Experimental: GPU_MEM_UTIL=0.88, MAX_MODEL_LEN=6144 (may OOM on warmup)

.PHONY: setup build build-llama \
	run-llm run-vision run-embed run-llama-llm run-qwen3 run-qwen3-fast run-qwen14 run-qwen14-balanced \
	run-qwen7b run-qwen2-vl-2b run-qwen2-vl-7b-awq run-devstral-small-24b run-devstral-small-24b-fast run-deepseek run-phi3p5-mini run-qwen2p5-1p5b run-qwen3-32b run-qwen3-coder \
	run-openwebui run-openwebui-with-llm \
	open-openwebui \
	stop stop-all stop-llm stop-embed stop-llama-llm stop-openwebui \
	logs logs-llm logs-embed \
	logs-openwebui \
	healthcheck healthcheck-llm healthcheck-embed healthcheck-openwebui \
	models shell clean clean-all presets

# ── Setup / Build ───────────────────────────────────────

setup:
	mkdir -p $(CACHE_PATH)

build:
	docker build -t $(IMAGE) .

build-llama:
	docker build -t $(LLAMA_IMAGE) -f Dockerfile.llamacpp .

# ── Run: vLLM LLM server ───────────────────────────────

run-llm: stop-llm
	docker network inspect $(DOCKER_NETWORK) >/dev/null 2>&1 || docker network create $(DOCKER_NETWORK)
	docker run -d \
		--name $(LLM_CONTAINER) \
		--network $(DOCKER_NETWORK) \
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
	docker logs $(LLM_CONTAINER) --follow

# 2×RTX 3090 tuning helpers (24 GB each)

# Qwen3-32B AWQ (safety-first profile)
run-qwen3:
	$(MAKE) run-llm PRESET=QWEN3_32B_AWQ GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.76 MAX_MODEL_LEN=3072 EXTRA_ARGS="--max-num-seqs 1"

run-qwen3-fast:
	$(MAKE) run-llm PRESET=QWEN3_32B_AWQ GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.80 MAX_MODEL_LEN=4096 EXTRA_ARGS="--max-num-seqs 2"

# Qwen3 32B AWQ (dual GPU first-pass profile)
run-qwen3-32b:
	$(MAKE) run-llm PRESET=QWEN3_32B_AWQ GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.76 MAX_MODEL_LEN=3072 EXTRA_ARGS="--max-num-seqs 1"

# Qwen3 30B coder A3B instruct (dual GPU first-pass profile)
run-qwen3-coder:
	$(MAKE) run-llm PRESET=QWEN3_CODER_30B_A3B_INSTRUCT GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.76 MAX_MODEL_LEN=3072 EXTRA_ARGS="--max-num-seqs 1"

# Qwen2.5-14B-AWQ (dual GPU baseline)
run-qwen14:
	$(MAKE) run-llm PRESET=QWEN_14B_AWQ GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.78 MAX_MODEL_LEN=8192 EXTRA_ARGS="--max-num-seqs 2"

# Qwen2.5-14B-AWQ (more context headroom)
run-qwen14-balanced:
	$(MAKE) run-llm PRESET=QWEN_14B_AWQ GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.80 MAX_MODEL_LEN=12288 EXTRA_ARGS="--max-num-seqs 1"

# Qwen2.5-7B-AWQ (single GPU, GPU1 default, fast default target for terminal/agents)
run-qwen7b:
	$(MAKE) run-llm PRESET=QWEN_7B_AWQ GPU=1 TP_SIZE=1 GPU_MEM_UTIL=0.88 MAX_MODEL_LEN=4096 EXTRA_ARGS="--max-num-seqs 2 --max-num-batched-tokens 4096"

# Qwen2-VL-2B-Instruct (single GPU, GPU1 default)
run-qwen2-vl-2b:
	$(MAKE) run-llm PRESET=QWEN_VL_2B GPU=1 TP_SIZE=1 GPU_MEM_UTIL=0.88 MAX_MODEL_LEN=8192 EXTRA_ARGS="--max-num-seqs 4"

# Qwen2-VL-7B-AWQ (single GPU, GPU1 default)
run-qwen2-vl-7b-awq:
	$(MAKE) run-llm PRESET=QWEN2_VL_7B_AWQ GPU=1 TP_SIZE=1 GPU_MEM_UTIL=0.86 MAX_MODEL_LEN=8192 EXTRA_ARGS="--max-num-seqs 4"

# Mistral Devstral Small 24B (FP8, long-context, single-user tuned)
run-devstral-small-24b:
	$(MAKE) run-llm PRESET=DEVSTRAL_SMALL_24B GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.78 MAX_MODEL_LEN=65536 EXTRA_ARGS="--max-num-seqs 1"

# Mistral Devstral Small 24B (same model, smaller context for extra safety)
run-devstral-small-24b-fast:
	$(MAKE) run-llm PRESET=DEVSTRAL_SMALL_24B GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.80 MAX_MODEL_LEN=32768 EXTRA_ARGS="--max-num-seqs 1"

# DeepSeek R1 Distill Qwen 32B (dual GPU first-pass profile)
run-deepseek:
	$(MAKE) run-llm PRESET=DEEPSEEK_R1_QWEN_32B GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.72 MAX_MODEL_LEN=3072 EXTRA_ARGS="--max-num-seqs 1"

# Phi-3.5 Mini instruct (single GPU, GPU1 default, low-concurrency + longer context)
run-phi3p5-mini:
	$(MAKE) run-llm PRESET=PHI3P5_MINI_INSTRUCT GPU=1 TP_SIZE=1 GPU_MEM_UTIL=0.92 MAX_MODEL_LEN=16384 EXTRA_ARGS="--max-num-seqs 1 --max-num-batched-tokens 4096"

# Qwen2.5-Instruct-1.5B (single GPU, GPU1 default)
run-qwen2p5-1p5b:
	$(MAKE) run-llm PRESET=QWEN2P5_INSTRUCT_1P5B GPU=1 TP_SIZE=1 GPU_MEM_UTIL=0.90 MAX_MODEL_LEN=8192 EXTRA_ARGS="--max-num-seqs 4"

run-vision:
	$(MAKE) run-llm PRESET=QWEN3_VL_30B_FP8 GPU=all TP_SIZE=2 GPU_MEM_UTIL=0.80 MAX_MODEL_LEN=4096 EXTRA_ARGS="--max-num-seqs 2"

# ── Run: Open WebUI chat frontend ─────────────────────

run-openwebui: stop-openwebui
	docker network inspect $(DOCKER_NETWORK) >/dev/null 2>&1 || docker network create $(DOCKER_NETWORK)
	docker run -d \
		--name $(OPEN_WEBUI_CONTAINER) \
		--network $(DOCKER_NETWORK) \
		-p $(OPEN_WEBUI_PORT):8080 \
		-v $(OPEN_WEBUI_DATA):/app/backend/data \
		--restart unless-stopped \
		-e WEBUI_AUTH=false \
		-e OPENAI_API_BASE_URL=$(OPEN_WEBUI_VLLM_BASE_URL) \
		-e OPENAI_API_BASE_URLS=$(OPEN_WEBUI_VLLM_BASE_URL) \
		-e OPENAI_API_KEY=$(OPEN_WEBUI_VLLM_API_KEY) \
		-e OPENAI_API_KEYS=$(OPEN_WEBUI_VLLM_API_KEY) \
		$(OPEN_WEBUI_IMAGE)

run-openwebui-with-llm:
	$(MAKE) run-llm PRESET=$(OPEN_WEBUI_PRESET) GPU=$(OPEN_WEBUI_GPU) >/tmp/run-llm.log 2>&1 & \
	sleep 1
	$(MAKE) run-openwebui

open-openwebui:
	@nohup chromium --new-tab http://localhost:$(OPEN_WEBUI_PORT) >/tmp/openwebui.log 2>&1 &

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

stop-openwebui:
	docker stop $(OPEN_WEBUI_CONTAINER) 2>/dev/null || true
	docker rm $(OPEN_WEBUI_CONTAINER) 2>/dev/null || true

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

logs-openwebui:
	docker logs -f $(OPEN_WEBUI_CONTAINER)

# ── Healthcheck ─────────────────────────────────────────

healthcheck:
	@curl -sf http://localhost:$(PORT)/health && echo "healthy" || echo "unhealthy"

healthcheck-llm:
	@curl -sf http://localhost:$(PORT)/health && echo "healthy" || echo "unhealthy"

healthcheck-embed:
	@curl -sf http://localhost:$(LLAMA_PORT)/health && echo "healthy" || echo "unhealthy"

healthcheck-openwebui:
	@curl -sf http://localhost:$(OPEN_WEBUI_PORT)/health && echo "healthy" || echo "unhealthy"

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
