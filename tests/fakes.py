from typing import Any

from comfy_helper.domain.models import Artifact, JobStatus
from comfy_helper.providers.base import (
    GenerationProvider,
    ProviderArtifactContent,
    ProviderHealth,
    ProviderJobSnapshot,
    ProviderSubmission,
)


class FakeProvider(GenerationProvider):
    name = "comfyui"

    def __init__(self) -> None:
        self.submitted_workflow: dict[str, Any] | None = None

    async def health(self) -> ProviderHealth:
        return ProviderHealth(name=self.name, status="ok", version="test")

    async def submit(
        self, workflow: dict[str, Any], client_id: str
    ) -> ProviderSubmission:
        self.submitted_workflow = workflow
        return ProviderSubmission(id="provider-job-1", queue_number=1)

    async def get_job(self, provider_job_id: str) -> ProviderJobSnapshot:
        return ProviderJobSnapshot(
            status=JobStatus.succeeded,
            artifacts=[
                Artifact(
                    filename="generated.png",
                    source_url="http://comfy/view?filename=generated.png",
                )
            ],
        )

    async def model_inventory(self) -> dict[str, list[str]]:
        return {"diffusion_models": ["anima-turbo-v1.0.safetensors"]}

    async def download_artifact(self, artifact: Artifact) -> ProviderArtifactContent:
        return ProviderArtifactContent(
            content=b"generated-image", content_type="image/png"
        )
