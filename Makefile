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
# Note: 8192 context OOMs on warmup; 4096 is stable
GPU_MEM_UTIL := 0.85
MAX_MODEL_LEN := 4096
PORT := 8000

# Tuning notes (RTX 5000 16GB):
#   Default (stable): GPU_MEM_UTIL=0.85, MAX_MODEL_LEN=4096
#   If OOM: try --enforce-eager to disable CUDA graphs
#   Experimental: GPU_MEM_UTIL=0.88, MAX_MODEL_LEN=6144 (may OOM on warmup)

.PHONY: build run run-detached stop logs healthcheck shell clean setup

setup:
	mkdir -p $(CACHE_PATH)

build:
	docker build -t $(IMAGE) .

run:
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

run-detached:
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

logs:
	docker logs -f $(CONTAINER_NAME)

healthcheck:
	@curl -sf http://localhost:$(PORT)/health && echo "healthy" || echo "unhealthy"

# Quick model list check
models:
	@curl -s http://localhost:$(PORT)/v1/models | python3 -m json.tool

shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

clean: stop
	docker rmi $(IMAGE) || true

# Experimental: higher context (may OOM on warmup)
run-experimental:
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
