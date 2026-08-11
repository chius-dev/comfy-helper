from typing import Any

import httpx
import pytest

from comfy_helper.api import create_app
from comfy_helper.config import Settings
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


@pytest.fixture
async def client_and_provider(tmp_path):
    provider = FakeProvider()
    settings = Settings(artifact_dir=tmp_path)
    transport = httpx.ASGITransport(
        app=create_app(settings=settings, provider=provider)
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, provider


@pytest.mark.asyncio
async def test_health_reports_gateway_and_provider_status(client_and_provider) -> None:
    client, _ = client_and_provider
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "comfy-helper",
        "provider": {
            "name": "comfyui",
            "status": "ok",
            "detail": None,
            "version": "test",
        },
    }


@pytest.mark.asyncio
async def test_core_resources_list_provider_and_workflow_profile(
    client_and_provider,
) -> None:
    client, _ = client_and_provider

    providers = await client.get("/api/v1/providers")
    profiles = await client.get("/api/v1/workflow-profiles")
    profile = await client.get("/api/v1/workflow-profiles/anima-turbo-t2i")

    assert providers.json()[0]["name"] == "comfyui"
    assert providers.json()[0]["models"]["diffusion_models"] == [
        "anima-turbo-v1.0.safetensors"
    ]
    assert profiles.json()[0]["id"] == "anima-turbo-t2i"
    assert profile.json()["model_family"] == "anima"
    assert "template" not in profile.json()


def test_openapi_hides_provider_job_id() -> None:
    properties = create_app(provider=FakeProvider()).openapi()["components"]["schemas"][
        "GenerationJob"
    ]["properties"]

    assert "provider_job_id" not in properties


@pytest.mark.asyncio
async def test_generation_submission_creates_refreshable_job(
    client_and_provider,
) -> None:
    client, provider = client_and_provider

    created = await client.post(
        "/api/v1/generations",
        json={
            "profile_id": "anima-turbo-t2i",
            "prompt": "1girl, blue hair",
            "seed": 123,
        },
    )
    assert created.status_code == 202
    job = created.json()
    assert job["status"] == "queued"
    assert "provider_job_id" not in job
    assert provider.submitted_workflow["4"]["inputs"]["text"] == "1girl, blue hair"

    refreshed = await client.get(f"/api/v1/jobs/{job['id']}")
    artifacts = await client.get(f"/api/v1/jobs/{job['id']}/artifacts")

    assert refreshed.json()["status"] == "succeeded"
    assert "provider_job_id" not in refreshed.json()
    assert artifacts.json()[0]["filename"] == "generated.png"


@pytest.mark.asyncio
async def test_stored_artifact_is_retrievable_through_gateway(
    client_and_provider,
) -> None:
    client, _ = client_and_provider
    created = await client.post(
        "/api/v1/generations",
        json={"profile_id": "anima-turbo-t2i", "prompt": "artifact test"},
    )
    refreshed = await client.get(f"/api/v1/jobs/{created.json()['id']}")

    artifact = refreshed.json()["artifacts"][0]
    response = await client.get(artifact["url"])

    assert artifact["url"] == f"/api/v1/artifacts/{artifact['id']}"
    assert response.status_code == 200
    assert response.content == b"generated-image"
    assert response.headers["content-type"] == "image/png"
