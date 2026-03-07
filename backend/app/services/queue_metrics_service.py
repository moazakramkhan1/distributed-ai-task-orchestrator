from typing import Optional

from app.core.config import settings
from app.services.health_service import get_redis_client


def get_queue_depth() -> Optional[int]:
    try:
        r = get_redis_client()
        length = r.llen(settings.CELERY_QUEUE_NAME)
        return int(length)
    except Exception:
        return None


def infer_scaling_status(
    queue_depth: Optional[int],
    desired: Optional[int],
    ready: Optional[int],
    previous_desired: Optional[int] = None,
) -> str:
    if desired is None or ready is None:
        return "degraded"
    if queue_depth is None:
        return "degraded"
    if queue_depth == 0 and desired <= 1:
        return "idle"
    if previous_desired is not None:
        if desired > previous_desired:
            return "scaling_up"
        if desired < previous_desired:
            return "scaling_down"
    if ready < desired:
        return "scaling_up"
    if queue_depth > 0 and desired >= ready:
        return "stable"
    return "stable"
