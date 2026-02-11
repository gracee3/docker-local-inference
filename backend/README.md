# Homeschool Backend (Axum + SQLx + SQLite)

Local-first API for small households, designed to run next to a local LLM HTTP endpoint.

## Project Layout

- `src/main.rs`: HTTP server bootstrap and route registration.
- `src/config.rs`: environment-driven runtime config.
- `src/db.rs`: SQLite pool setup, WAL/synchronous PRAGMAs, migration execution.
- `src/app_state.rs`: shared app state (`SqlitePool`, `reqwest::Client`, config).
- `src/error.rs`: API error mapping to HTTP responses.
- `src/routes/health.rs`: health endpoint.
- `src/routes/students.rs`: starter CRUD-style student endpoints.
- `src/routes/llm.rs`: local LLM proxy endpoint that persists interactions.
- `migrations/*.sql`: schema and starter data.

## Quick Start

```bash
cd backend
cp .env.example .env
cargo run
```

Server defaults to `http://127.0.0.1:3000`.

## Endpoints

- `GET /healthz`
- `GET /students`
- `POST /students`
- `POST /llm/chat`

### `POST /students`

```json
{
  "name": "Avery",
  "grade_level": "6"
}
```

### `POST /llm/chat`

```json
{
  "user_id": 1,
  "student_id": 1,
  "payload": {
    "model": "/model",
    "messages": [
      { "role": "user", "content": "Explain fractions for a 5th grader." }
    ]
  }
}
```

`payload` is forwarded as-is to `${LLM_BASE_URL}${LLM_CHAT_PATH}` and both prompt/response are persisted in `ai_interactions`.

## Environment

See `.env.example`:

- `APP_HOST`
- `APP_PORT`
- `DATABASE_URL` (default `sqlite://data/app.db`)
- `LLM_BASE_URL` (default `http://127.0.0.1:8000`)
- `LLM_CHAT_PATH` (default `/v1/chat/completions`)
- `RUST_LOG`
