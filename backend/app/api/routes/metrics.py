from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskResponse
from app.services.k8s_service import get_worker_deployment_status
from app.services.queue_metrics_service import get_queue_depth, infer_scaling_status
from app.services.task_service import get_recent_completed, get_tasks_by_status_counts

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


@router.get("/workers")
def worker_metrics():
    dep = get_worker_deployment_status()
    queue_depth = get_queue_depth()
    status = infer_scaling_status(
        queue_depth=queue_depth,
        desired=dep["desired_replicas"],
        ready=dep["ready_replicas"],
    )
    return {
        "desired_replicas": dep["desired_replicas"],
        "available_replicas": dep["available_replicas"],
        "ready_replicas": dep["ready_replicas"],
        "min_replicas": dep["min_replicas"],
        "max_replicas": dep["max_replicas"],
        "queue_depth": queue_depth,
        "scaling_status": status,
        "k8s_available": dep["k8s_available"],
    }


@router.get("/autoscaling/events")
def autoscaling_events():
    dep = get_worker_deployment_status()
    queue_depth = get_queue_depth()
    status = infer_scaling_status(
        queue_depth=queue_depth,
        desired=dep["desired_replicas"],
        ready=dep["ready_replicas"],
    )
    return {
        "queue_depth": queue_depth,
        "available_replicas": dep["available_replicas"],
        "desired_replicas": dep["desired_replicas"],
        "ready_replicas": dep["ready_replicas"],
        "status": status,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "k8s_available": dep["k8s_available"],
    }
