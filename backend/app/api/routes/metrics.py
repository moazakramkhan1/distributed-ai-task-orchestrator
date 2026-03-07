from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskResponse
from app.services.task_service import get_tasks_by_status_counts, get_recent_completed

router = APIRouter(prefix="/metrics")


@router.get("/queue")
def queue_metrics(db: Session = Depends(get_db)):
    counts = get_tasks_by_status_counts(db)
    return {
        "pending": counts.get(TaskStatus.PENDING, 0),
        "in_progress": counts.get(TaskStatus.IN_PROGRESS, 0),
        "completed": counts.get(TaskStatus.COMPLETED, 0),
        "failed": counts.get(TaskStatus.FAILED, 0),
        "total": sum(counts.values()),
    }


@router.get("/results", response_model=List[TaskResponse])
def results_log(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_recent_completed(db, limit=limit)
