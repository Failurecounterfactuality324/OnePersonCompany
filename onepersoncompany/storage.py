from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from .config import settings
from .models import Artifact, ArtifactType, Task, TaskStatus


class JsonStorage:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.data_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.base_dir / "tasks.json"
        self.artifacts_file = self.base_dir / "artifacts.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.tasks_file.exists():
            self.tasks_file.write_text("[]", encoding="utf-8")
        if not self.artifacts_file.exists():
            self.artifacts_file.write_text("[]", encoding="utf-8")

    def _read_json(self, file_path: Path) -> List[Dict[str, Any]]:
        raw = file_path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Recover from partial writes by truncating to the outermost JSON array.
            left = raw.find("[")
            right = raw.rfind("]")
            if left != -1 and right != -1 and right > left:
                try:
                    return json.loads(raw[left : right + 1])
                except json.JSONDecodeError:
                    return []
            return []

    def _write_json(self, file_path: Path, payload: List[Dict[str, Any]]) -> None:
        tmp_file = file_path.with_suffix(f"{file_path.suffix}.tmp")
        tmp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(str(tmp_file), str(file_path))

    def create_task(self, title: str, priority: int = 3, source: str = "manual") -> Task:
        task = Task(id=str(uuid4()), title=title, priority=priority, source=source)
        rows = self._read_json(self.tasks_file)
        rows.append(task.model_dump())
        self._write_json(self.tasks_file, rows)
        return task

    def list_tasks(self) -> List[Task]:
        rows = self._read_json(self.tasks_file)
        return [Task.model_validate(row) for row in rows]

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        rows = self._read_json(self.tasks_file)
        updated_row = None
        for row in rows:
            if row.get("id") == task_id:
                row["status"] = status.value
                updated_row = row
                break
        if updated_row is None:
            raise ValueError(f"Task not found: {task_id}")
        self._write_json(self.tasks_file, rows)
        return Task.model_validate(updated_row)

    def save_artifact(self, artifact_type: ArtifactType, title: str, content: str, metadata: Dict[str, str]) -> Artifact:
        artifact = Artifact(
            id=str(uuid4()),
            artifact_type=artifact_type,
            title=title,
            content=content,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )
        rows = self._read_json(self.artifacts_file)
        rows.append(artifact.model_dump(mode="json"))
        self._write_json(self.artifacts_file, rows)
        return artifact

    def list_artifacts(self, artifact_type: ArtifactType | None = None) -> List[Artifact]:
        rows = self._read_json(self.artifacts_file)
        artifacts = [Artifact.model_validate(row) for row in rows]
        if artifact_type is None:
            return artifacts
        return [item for item in artifacts if item.artifact_type == artifact_type]

    def get_latest_artifact(self, artifact_type: ArtifactType | None = None) -> Artifact | None:
        artifacts = self.list_artifacts(artifact_type=artifact_type)
        if not artifacts:
            return None
        return sorted(artifacts, key=lambda item: item.created_at)[-1]
