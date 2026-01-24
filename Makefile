# vLLM Qwen2.5-14B-Instruct-AWQ Server
# Tuned for RTX 5000 16GB + 96GB RAM

IMAGE_NAME := local/vllm-qwen
IMAGE_TAG := 0.11.0
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)
CONTAINER_NAME := vllm-qwen

# Paths
MODEL_PATH := /data/models/Qwen2.5-14B-Instruct-AWQ
CACHE_PATH := $(HOME)/.cache/vllm

# vLLM settings (tuned for RTX 5000 16GB)
# Note: 8192 context may OOM on warmup; 4096 is stable
GPU_MEM_UTIL := 0.85
MAX_MODEL_LEN := 8192
PORT := 8000

# Tuning notes (RTX 5000 16GB):
#   Default (stable): GPU_MEM_UTIL=0.85, MAX_MODEL_LEN=4096
#   If OOM: try --enforce-eager to disable CUDA graphs
#   Experimental: GPU_MEM_UTIL=0.88, MAX_MODEL_LEN=6144 (may OOM on warmup)

# All container names used by this project
CONTAINERS := vllm-qwen vllm-vision

.PHONY: build run run-detached run-vision stop stop-all logs healthcheck shell clean clean-all setup

setup:
	mkdir -p $(CACHE_PATH)

build:
	docker build -t $(IMAGE) .

run: stop-all
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		--gpus all \
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
		--gpus all \
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

stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

stop-all:
	@for c in $(CONTAINERS); do \
		docker stop $$c 2>/dev/null || true; \
		docker rm $$c 2>/dev/null || true; \
	done
	@echo "All containers stopped"

logs:
	@for c in $(CONTAINERS); do \
		if docker ps --format '{{.Names}}' | grep -q "^$$c$$"; then \
			docker logs -f $$c; \
			exit 0; \
		fi; \
	done; \
	echo "No running container found"

healthcheck:
	@curl -sf http://localhost:$(PORT)/health && echo "healthy" || echo "unhealthy"

# Quick model list check
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

clean: stop
	docker rmi $(IMAGE) || true

clean-all: stop-all
	docker rmi $(IMAGE) || true

# Vision model (default: Qwen2-VL-7B-Instruct-AWQ)
# Usage: make run-vision
# Usage: make run-vision VISION_MODEL=/data/models/Qwen2-VL-2B-Instruct
VISION_MODEL := /data/models/Qwen2-VL-7B-Instruct-AWQ

run-vision: stop-all
	docker run -d \
		--name vllm-vision \
		--gpus all \
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

# Experimental: higher context (may OOM on warmup)
run-experimental: stop-all
	docker run --rm -it \
		--name $(CONTAINER_NAME) \
		--gpus all \
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
