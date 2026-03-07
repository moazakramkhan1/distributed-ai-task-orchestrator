from typing import Dict
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate


def create_task(db: Session, task_in: TaskCreate) -> Task:
    task = Task(input_text=task_in.input_text)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: UUID) -> Task | None:
    return db.query(Task).filter(Task.id == task_id).first()


def get_all_tasks(db: Session) -> list[Task]:
    return db.query(Task).order_by(Task.created_at.desc()).all()


def get_tasks_by_status_counts(db: Session) -> Dict[TaskStatus, int]:
    rows = db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    return {status: count for status, count in rows}


def get_recent_completed(db: Session, limit: int = 20) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.status == TaskStatus.COMPLETED)
        .order_by(Task.updated_at.desc())
        .limit(limit)
        .all()
    )
