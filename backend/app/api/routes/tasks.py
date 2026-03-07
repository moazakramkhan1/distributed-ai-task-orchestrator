from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.task import BulkTaskCreate, BulkTaskResponse, TaskCreate, TaskResponse
from app.services.task_service import create_task, get_all_tasks, get_task
from app.worker.tasks import process_task

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    task = create_task(db, task_in)
    process_task.delay(str(task.id))
    return task


@router.post("/tasks/bulk", response_model=BulkTaskResponse, status_code=status.HTTP_201_CREATED)
def create_bulk_tasks(body: BulkTaskCreate, db: Session = Depends(get_db)):
    ids = []
    for item in body.items:
        task = create_task(db, item)
        process_task.delay(str(task.id))
        ids.append(str(task.id))
    return {"count": len(ids), "task_ids": ids}


@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    return get_all_tasks(db)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_by_id(task_id: UUID, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
