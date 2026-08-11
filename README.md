# comfy-helper

A gateway-first FastAPI service for named ComfyUI generation workflows. The API exposes provider-neutral profiles, jobs, and artifacts while keeping ComfyUI graph details inside workflow profiles and provider adapters.

## Current scope

- environment-backed configuration;
- FastAPI application and OpenAPI schema;
- provider abstraction plus a ComfyUI REST adapter;
- generation/job/artifact domain models;
- in-memory job orchestration with filesystem-backed artifact storage;
- an installed-model-compatible `anima-turbo-t2i` profile;
- health, provider, profile, generation, job, and artifact endpoints;
- unit/API tests.

See [docs/architecture.md](docs/architecture.md) for boundaries, decisions, live environment findings, and next steps.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended)
- reachable ComfyUI server; default: `http://10.0.0.180:8188/`

## Run locally

```bash
cp .env.example .env
uv sync --extra dev
uv run comfy-helper
```

The gateway listens on `http://127.0.0.1:8000` by default. Interactive API docs are at `http://127.0.0.1:8000/docs`.

Alternative invocation:

```bash
uv run uvicorn comfy_helper.api:app --host 127.0.0.1 --port 8000
```

## Configuration

Settings use the `COMFY_HELPER_` prefix and can be placed in `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `COMFY_HELPER_HOST` | `127.0.0.1` | Gateway bind address |
| `COMFY_HELPER_PORT` | `8000` | Gateway port |
| `COMFY_HELPER_COMFYUI_URL` | `http://10.0.0.180:8188/` | ComfyUI base URL |
| `COMFY_HELPER_COMFYUI_TIMEOUT_SECONDS` | `10` | Provider HTTP timeout |
| `COMFY_HELPER_ARTIFACT_DIR` | `artifacts` | Directory for gateway-owned output files |

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Gateway and provider health |
| `GET` | `/api/v1/providers` | Provider health and model inventory |
| `GET` | `/api/v1/workflow-profiles` | Available named profiles |
| `GET` | `/api/v1/workflow-profiles/{id}` | Profile metadata/defaults |
| `POST` | `/api/v1/generations` | Render and enqueue a generation |
| `GET` | `/api/v1/jobs/{id}` | Refresh and return a job |
| `GET` | `/api/v1/jobs/{id}/artifacts` | Return generated artifacts |
| `GET` | `/api/v1/artifacts/{id}` | Retrieve stored artifact bytes |

Example submission:

```bash
curl -sS http://127.0.0.1:8000/api/v1/generations \
  -H 'content-type: application/json' \
  -d '{
    "profile_id": "anima-turbo-t2i",
    "prompt": "masterpiece, best quality, 1girl, blue hair, anime style",
    "width": 1024,
    "height": 1024,
    "seed": 42
  }'
```

`seed` may be omitted; the current skeleton then uses profile seed `0`. Random seed policy is intentionally deferred until job persistence records the selected seed reliably.

## Development

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
```

For the complete real execution and verification procedure, see [docs/end-to-end.md](docs/end-to-end.md).

Jobs and artifact metadata are currently stored in memory; artifact bytes are stored under `COMFY_HELPER_ARTIFACT_DIR`. This is suitable for a single-process gateway. Restart-safe job lookup is intentionally deferred.
