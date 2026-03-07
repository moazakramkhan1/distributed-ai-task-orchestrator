import time
from uuid import UUID

from celery.exceptions import MaxRetriesExceededError
from celery.signals import worker_ready, heartbeat_sent

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.services.groq_service import analyze_text
from app.services.health_service import set_worker_heartbeat
from app.worker.celery_app import celery_app

_MAX_RETRIES = 3
_RETRY_COUNTDOWN = 10


@worker_ready.connect
def on_worker_ready(**kwargs):
    set_worker_heartbeat()


@heartbeat_sent.connect
def on_heartbeat(**kwargs):
    set_worker_heartbeat()


@celery_app.task(name="process_task", bind=True, max_retries=_MAX_RETRIES)
def process_task(self, task_id: str):
    set_worker_heartbeat()
    db = SessionLocal()
    try:
        task = (
            db.query(Task)
            .filter(Task.id == UUID(task_id))
            .with_for_update(skip_locked=True)
            .first()
        )
        if not task:
            return

        if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED):
            return

        task.status = TaskStatus.IN_PROGRESS
        db.commit()

        if settings.SIMULATE_AI_FAILURE and "FAIL_TEST" in task.input_text:
            raise RuntimeError("Simulated failure triggered by FAIL_TEST keyword")

        time.sleep(2)

        analysis = analyze_text(task.input_text)

        task.result = analysis
        task.status = TaskStatus.COMPLETED
        db.commit()

    except MaxRetriesExceededError:
        db.rollback()
        db2 = SessionLocal()
        try:
            t = db2.query(Task).filter(Task.id == UUID(task_id)).first()
            if t:
                t.status = TaskStatus.FAILED
                t.result = "Task failed after maximum retries."
                db2.commit()
        finally:
            db2.close()

    except Exception as exc:
        db.rollback()
        db2 = SessionLocal()
        try:
            t = db2.query(Task).filter(Task.id == UUID(task_id)).first()
            if t:
                t.retry_count += 1
                t.status = TaskStatus.PENDING
                db2.commit()
        finally:
            db2.close()

        try:
            raise self.retry(exc=exc, countdown=_RETRY_COUNTDOWN)
        except MaxRetriesExceededError:
            db3 = SessionLocal()
            try:
                t = db3.query(Task).filter(Task.id == UUID(task_id)).first()
                if t:
                    t.status = TaskStatus.FAILED
                    t.result = f"Task failed after {_MAX_RETRIES} retries. Last error: {exc}"
                    db3.commit()
            finally:
                db3.close()

    finally:
        db.close()
