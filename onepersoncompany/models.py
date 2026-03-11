from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    DAILY_BRIEF = "daily_brief"
    WEEKLY_REVIEW = "weekly_review"
    LAUNCH_PACK = "launch_pack"


class Language(str, Enum):
    ZH = "zh"
    EN = "en"


class TaskStatus(str, Enum):
    TODO = "todo"
    DONE = "done"
    BLOCKED = "blocked"


class InputUpdate(BaseModel):
    summary: str = Field(..., min_length=1)
    source: str = Field(default="manual")


class Task(BaseModel):
    id: str
    title: str
    priority: int = Field(default=3, ge=1, le=5)
    status: TaskStatus = TaskStatus.TODO
    source: str = "manual"


class Artifact(BaseModel):
    id: str
    artifact_type: ArtifactType
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, str] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent: str
    artifact: Artifact


class RunRequest(BaseModel):
    updates: List[InputUpdate] = Field(default_factory=list)
    lang: Language = Language.ZH
    context: Optional[Dict[str, str]] = None


class AddTaskRequest(BaseModel):
    title: str = Field(..., min_length=1)
    priority: int = Field(default=3, ge=1, le=5)
    source: str = "manual"


class UpdateTaskStatusRequest(BaseModel):
    task_id: str = Field(..., min_length=1)
    status: TaskStatus = TaskStatus.DONE


class ShareCopy(BaseModel):
    title: str
    content: str


class SharePack(BaseModel):
    title: str
    x_post: str
    moments_post: str
    xiaohongshu_post: str
