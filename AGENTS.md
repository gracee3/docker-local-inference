# AGENTS.md

## Purpose
This repository is a local inference wrapper for serving models from disk with Docker.

Primary goals are low operational overhead, predictable local behavior, and fast iteration.

## Repo Map
- `Makefile`: main entrypoint for local inference workflows.
- `scripts/`: helper scripts for model setup and runtime helpers.
- `compose.yml`: optional dual-service compose setup.
- `Dockerfile`, `Dockerfile.llamacpp`: runtime images for vLLM and llama.cpp.

## Working Rules For Agents
- Prefer minimal changes that keep current behavior intact.
- Keep docs and commands synchronized when adding or renaming workflows.
- Prefer host-persisted data paths over container-internal state.
- Do not introduce Compose requirements unless asked; Compose is optional here.

## Common Commands
- Inference presets: `make presets`
- Build images: `make build` and `make build-llama`
- Run LLM server: `make run-llm PRESET=QWEN_14B_AWQ GPU=1`
- Health check: `make healthcheck-llm`
- Open WebUI: `make run-openwebui`
- Open WebUI URL: `make open-openwebui`

## Persistence Expectations
- Models are host-mounted at `/data/models/...`.

## Done Criteria For Changes
- Commands in docs are runnable as written.
- vLLM + Open WebUI commands remain consistent with `Makefile` targets.
- Keep root docs concise and GitHub-readable.
