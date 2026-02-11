# docker-local-inference

Local inference stack plus a small local-first backend.

## What Is Here
- Dockerized local model serving with `vLLM` and `llama.cpp`
- Rust backend in `backend/` (`axum + sqlx + sqlite`)
- Optional `compose.yml` (not required for normal local usage)

## Quick Start

```bash
# 1) Build inference images
make build
make build-llama

# 2) Start LLM server (example preset)
make run-llm PRESET=QWEN_14B_AWQ GPU=0

# 3) Verify LLM health
make healthcheck-llm

# 4) Start backend API
cd backend
cp .env.example .env
cargo run
```

Backend default: `http://127.0.0.1:3000`

## Basic Commands
- List model presets: `make presets`
- Start embeddings server: `make run-embed PRESET=NOMIC_EMBED_CODE_Q6 GPU=1`
- Stop inference containers: `make stop-all`
- Tail logs: `make logs-llm`
- Backend compile check: `cd backend && cargo check`

## Persistence
- Model weights are host-mounted from `/data/models/...`.
- Backend data is persisted in SQLite.
- Default backend DB URL is `sqlite://data/app.db` (file at `backend/data/app.db`).

## API Endpoints (Backend)
- `GET /healthz`
- `GET /students`
- `POST /students`
- `POST /llm/chat`

See `backend/README.md` for request payload examples.

## License
MIT (see `LICENSE`).
