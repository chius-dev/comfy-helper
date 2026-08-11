import re
from pathlib import Path
from uuid import UUID

from comfy_helper.domain.models import Artifact
from comfy_helper.providers.base import ProviderArtifactContent


class ArtifactNotFoundError(KeyError):
    pass


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._artifacts: dict[UUID, Artifact] = {}

    def store(
        self,
        job_id: UUID,
        artifact: Artifact,
        content: ProviderArtifactContent,
    ) -> Artifact:
        suffix = Path(artifact.filename).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
            suffix = ".bin"
        directory = self._root / str(job_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{artifact.id}{suffix}"
        path.write_bytes(content.content)

        artifact.local_path = str(path)
        artifact.content_type = content.content_type
        artifact.size_bytes = len(content.content)
        artifact.url = f"/api/v1/artifacts/{artifact.id}"
        self._artifacts[artifact.id] = artifact
        return artifact

    def get(self, artifact_id: UUID) -> Artifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise ArtifactNotFoundError(str(artifact_id)) from exc
