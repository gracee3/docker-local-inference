# AGENTS.md

## Purpose
This repository runs local LLM inference and a local-first homeschool backend.
Primary goals are low operational overhead, predictable local behavior, and fast iteration.

## Repo Map
- `Makefile`: main entrypoint for local inference workflows.
- `scripts/`: helper scripts for model setup and runtime helpers.
- `backend/`: Rust API (`axum`) + SQLite (`sqlx`) + migrations.
- `compose.yml`: optional dual-service compose setup.
- `Dockerfile`, `Dockerfile.llamacpp`: runtime images for vLLM and llama.cpp.

## Working Rules For Agents
- Prefer minimal changes that keep current behavior intact.
- Keep docs and commands synchronized when adding or renaming workflows.
- Default to SQLite for local persistence unless explicitly asked to add external DB infra.
- Prefer host-persisted data paths over container-internal state.
- Do not introduce Compose requirements unless asked; Compose is optional here.

## Common Commands
- Inference presets: `make presets`
- Build images: `make build` and `make build-llama`
- Run LLM server: `make run-llm PRESET=QWEN_14B_AWQ GPU=0`
- Health check: `make healthcheck-llm`
- Run backend API: `cd backend && cp .env.example .env && cargo run`
- Check backend build: `cd backend && cargo check`

## Persistence Expectations
- Models are host-mounted at `/data/models/...`.
- Backend DB persists to SQLite file configured by `DATABASE_URL`.
- Default backend path is `backend/data/app.db` (`sqlite://data/app.db` from `backend/`).

## Done Criteria For Changes
- Commands in docs are runnable as written.
- `backend` compiles with `cargo check` if backend code changed.
- Inference command examples remain consistent with `Makefile` targets.
- Keep root docs concise and GitHub-readable.
