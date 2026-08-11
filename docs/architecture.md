# Architecture

## Intent

`comfy-helper` is a gateway, not a second workflow engine. Clients use stable domain resources (workflow profiles, generation jobs, and artifacts); provider adapters translate those resources to ComfyUI's prompt/history/view APIs. ComfyUI remains responsible for graph execution, queueing, and GPU lifecycle.

```text
Client
  │ REST /api/v1
  ▼
FastAPI transport ── health / profiles / generations / jobs / artifacts
  │
  ▼
GenerationService ── orchestration and gateway job state
  │                  │
  │                  └── WorkflowRegistry ── validated, named workflow profiles
  ▼
GenerationProvider (port)
  ▼
ComfyUIProvider (adapter) ── /system_stats /models/* /prompt /history/{id} /queue /view
  ▼
ComfyUI at 10.0.0.180:8188
```

## Boundaries

- **API (`api.py`)**: HTTP validation, response codes, resource routing. It does not know ComfyUI workflow node IDs.
- **Domain (`domain/models.py`)**: provider-neutral generation requests, jobs, statuses, and artifacts.
- **Application service (`services/generation.py`)**: renders a selected profile, submits it, and reconciles provider state into a gateway job.
- **Workflow profiles (`workflows/`)**: named, versionable graph templates plus defaults and parameter bindings. Node-specific knowledge stays here.
- **Provider port (`providers/base.py`)**: the contract required by the application service.
- **ComfyUI adapter (`providers/comfyui.py`)**: HTTP protocol details and translation of ComfyUI history outputs into artifacts.
- **Configuration (`config.py`)**: environment-backed process settings only.

Dependency direction is API → service/domain/ports; the ComfyUI adapter implements the provider port. Domain models do not import FastAPI or ComfyUI types.

## Resource lifecycle

1. A client discovers `/api/v1/workflow-profiles` and selects a profile.
2. `POST /api/v1/generations` validates provider-neutral inputs.
3. `GenerationService` renders a fresh API-format graph and submits it to the provider.
4. The gateway stores a job mapped to ComfyUI's `prompt_id` and returns HTTP 202.
5. `GET /api/v1/jobs/{id}` reconciles completed state from history and queued/running state from the ComfyUI queue.
6. The provider downloads completed outputs from ComfyUI `/view`.
7. `ArtifactStore` writes the bytes under the configured artifact directory using gateway-generated IDs.
8. Clients retrieve stored bytes from `/api/v1/artifacts/{id}` without direct access to ComfyUI.

If a newly submitted prompt is briefly absent from both history and queue, the adapter allows a five-second propagation grace period. After that, or immediately for an unknown prompt, it reports a failed provider job instead of leaving the gateway job queued forever.

## Current persistence and next boundary

The gateway keeps jobs and artifact metadata in process memory while artifact bytes are persisted to the filesystem. Restarting the service loses gateway job and artifact lookup metadata, while the files and ComfyUI history remain. A durable repository (SQLite/PostgreSQL) can replace the in-memory mapping without changing API or provider contracts.

Likely next implementation slices:

- background reconciliation and WebSocket/SSE progress;
- durable job and artifact repositories;
- cancellation and queue controls;
- artifact proxy/download policies instead of exposing provider URLs;
- workflow/profile schema versioning and stronger parameter bindings;
- WAI checkpoint discovery and a WAI-specific profile once a checkpoint is installed;
- authentication, quotas, idempotency keys, and multi-provider routing.

## Live environment findings (2026-08-09)

The configured ComfyUI endpoint was reachable and reported:

- Windows, ComfyUI `0.30.0`;
- NVIDIA GeForce RTX 4060 Laptop GPU with 8 GB VRAM;
- empty queue during inspection;
- diffusion model `anima-turbo-v1.0.safetensors`;
- text encoder `qwen_3_06b_base.safetensors` (reported by loader schema);
- VAE `qwen_image_vae.safetensors`;
- no checkpoint-format models in `models/checkpoints`.

The Windows checkout contains an API-format workflow at `user/default/workflows/Anima_Turbo_T2I_api.json`. The registered `anima-turbo-t2i` profile follows that graph and uses only built-in node types.

## Decisions

- **Profiles, not arbitrary workflows, are public resources.** Accepting arbitrary graphs would expose custom-node execution and make validation/security unbounded.
- **Provider job IDs stay internal.** Gateway IDs remain stable if storage or provider routing changes later.
- **Polling is the first transport.** It is simple and maps directly to ComfyUI history. Streaming can be additive.
- **Anima first.** It is the actually installed model family. WAI remains an intended family, not a fabricated runnable profile.
