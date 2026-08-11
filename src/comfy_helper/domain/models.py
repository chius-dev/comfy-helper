from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class GenerationRequest(BaseModel):
    profile_id: str
    prompt: str = Field(min_length=1)
    negative_prompt: str | None = None
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    seed: int | None = Field(default=None, ge=0, le=2**64 - 1)
    steps: int | None = Field(default=None, ge=1, le=1000)
    cfg: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def dimensions_are_multiples_of_eight(self) -> "GenerationRequest":
        if self.width % 8 or self.height % 8:
            raise ValueError("width and height must be multiples of 8")
        return self

    def workflow_parameters(self) -> dict[str, Any]:
        return self.model_dump(exclude={"profile_id"}, exclude_none=True)


class Artifact(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    kind: str = "image"
    filename: str
    subfolder: str = ""
    storage_type: str = "output"
    url: str | None = None
    source_url: str | None = Field(default=None, exclude=True)
    local_path: str | None = Field(default=None, exclude=True)
    content_type: str | None = None
    size_bytes: int | None = None


class GenerationJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    provider: str
    provider_job_id: str = Field(exclude=True)
    profile_id: str
    status: JobStatus = JobStatus.queued
    request: GenerationRequest
    artifacts: list[Artifact] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
