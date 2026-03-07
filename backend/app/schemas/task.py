from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    input_text: str


class TaskResponse(BaseModel):
    id: UUID
    input_text: str
    status: TaskStatus
    result: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkTaskCreate(BaseModel):
    items: List[TaskCreate]


class BulkTaskResponse(BaseModel):
    count: int
    task_ids: List[str]
