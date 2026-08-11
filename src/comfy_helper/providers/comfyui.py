from collections.abc import Callable
from time import monotonic
from typing import Any
from urllib.parse import urlencode

import httpx

from comfy_helper.domain.models import Artifact, JobStatus
from comfy_helper.providers.base import (
    GenerationProvider,
    ProviderArtifactContent,
    ProviderHealth,
    ProviderJobSnapshot,
    ProviderSubmission,
)


class ComfyUIProvider(GenerationProvider):
    name = "comfyui"

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
        missing_prompt_grace_seconds: float = 5.0,
        clock: Callable[[], float] = monotonic,
        max_artifact_bytes: int = 50 * 1024 * 1024,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url, timeout=timeout
        )
        self._missing_prompt_grace_seconds = missing_prompt_grace_seconds
        self._clock = clock
        self._max_artifact_bytes = max_artifact_bytes
        self._submitted_at: dict[str, float] = {}

    async def health(self) -> ProviderHealth:
        try:
            response = await self._client.get("system_stats")
            response.raise_for_status()
            version = response.json().get("system", {}).get("comfyui_version")
            return ProviderHealth(name=self.name, status="ok", version=version)
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderHealth(name=self.name, status="unavailable", detail=str(exc))

    async def submit(
        self, workflow: dict[str, Any], client_id: str
    ) -> ProviderSubmission:
        response = await self._client.post(
            "prompt", json={"prompt": workflow, "client_id": client_id}
        )
        response.raise_for_status()
        payload = response.json()
        self._submitted_at[payload["prompt_id"]] = self._clock()
        return ProviderSubmission(
            id=payload["prompt_id"], queue_number=payload.get("number")
        )

    async def get_job(self, provider_job_id: str) -> ProviderJobSnapshot:
        response = await self._client.get(f"history/{provider_job_id}")
        response.raise_for_status()
        entry = response.json().get(provider_job_id)
        if entry is None:
            return await self._queue_snapshot(provider_job_id)

        status_data = entry.get("status", {})
        status = self._map_status(status_data)
        if status in {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}:
            self._submitted_at.pop(provider_job_id, None)
        artifacts = self._extract_artifacts(entry.get("outputs", {}))
        error = None
        if status is JobStatus.failed:
            error = self._extract_error(status_data)
        return ProviderJobSnapshot(status=status, artifacts=artifacts, error=error)

    async def model_inventory(self) -> dict[str, list[str]]:
        folders = ("checkpoints", "diffusion_models", "vae", "text_encoders")
        inventory: dict[str, list[str]] = {}
        for folder in folders:
            response = await self._client.get(f"models/{folder}")
            response.raise_for_status()
            inventory[folder] = response.json()
        return inventory

    def _extract_artifacts(self, outputs: dict[str, Any]) -> list[Artifact]:
        artifacts: list[Artifact] = []
        for output in outputs.values():
            for image in output.get("images", []):
                query = urlencode(
                    {
                        "filename": image["filename"],
                        "subfolder": image.get("subfolder", ""),
                        "type": image.get("type", "output"),
                    }
                )
                artifacts.append(
                    Artifact(
                        filename=image["filename"],
                        subfolder=image.get("subfolder", ""),
                        storage_type=image.get("type", "output"),
                        source_url=f"{self._base_url}view?{query}",
                    )
                )
        return artifacts

    async def download_artifact(self, artifact: Artifact) -> ProviderArtifactContent:
        from comfy_helper.services.artifacts import ArtifactTooLargeError

        async with self._client.stream(
            "GET",
            "view",
            params={
                "filename": artifact.filename,
                "subfolder": artifact.subfolder,
                "type": artifact.storage_type,
            },
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get(
                "content-type", "application/octet-stream"
            )
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > self._max_artifact_bytes:
                    raise ArtifactTooLargeError(
                        f"artifact exceeds max size of {self._max_artifact_bytes} bytes"
                    )
                chunks.append(chunk)
        return ProviderArtifactContent(
            content=b"".join(chunks),
            content_type=content_type.split(";", 1)[0],
        )

    async def _queue_snapshot(self, provider_job_id: str) -> ProviderJobSnapshot:
        response = await self._client.get("queue")
        response.raise_for_status()
        queue = response.json()
        if self._queue_contains(queue.get("queue_running", []), provider_job_id):
            return ProviderJobSnapshot(status=JobStatus.running)
        if self._queue_contains(queue.get("queue_pending", []), provider_job_id):
            return ProviderJobSnapshot(status=JobStatus.queued)
        submitted_at = self._submitted_at.get(provider_job_id)
        if (
            submitted_at is not None
            and self._clock() - submitted_at <= self._missing_prompt_grace_seconds
        ):
            return ProviderJobSnapshot(status=JobStatus.queued)
        self._submitted_at.pop(provider_job_id, None)
        return ProviderJobSnapshot(
            status=JobStatus.failed,
            error="ComfyUI prompt is absent from history and queue",
        )

    @staticmethod
    def _queue_contains(entries: list[Any], provider_job_id: str) -> bool:
        return any(
            isinstance(entry, list) and len(entry) > 1 and entry[1] == provider_job_id
            for entry in entries
        )

    @staticmethod
    def _map_status(status: dict[str, Any]) -> JobStatus:
        if status.get("status_str") in {"error", "failed"}:
            return JobStatus.failed
        if status.get("completed") and status.get("status_str") == "success":
            return JobStatus.succeeded
        return JobStatus.running

    @staticmethod
    def _extract_error(status: dict[str, Any]) -> str:
        for message in reversed(status.get("messages", [])):
            if not isinstance(message, list) or len(message) != 2:
                continue
            message_type, details = message
            if message_type != "execution_error" or not isinstance(details, dict):
                continue
            error_type = details.get("exception_type")
            error_message = details.get("exception_message")
            if error_type and error_message:
                return f"{error_type}: {error_message}"
            if error_message:
                return str(error_message)
        return str(status.get("status_str", "ComfyUI execution failed"))

    async def close(self) -> None:
        await self._client.aclose()
