import redis as redis_lib

from app.core.config import settings

_HEARTBEAT_KEY = "worker:heartbeat"


def get_redis_client() -> redis_lib.Redis:
    return redis_lib.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)


def get_redis_health() -> str:
    try:
        r = get_redis_client()
        r.ping()
        return "ok"
    except Exception:
        return "down"


def get_worker_health() -> str:
    try:
        r = get_redis_client()
        value = r.get(_HEARTBEAT_KEY)
        if value is None:
            return "degraded"
        return "ok"
    except Exception:
        return "degraded"


def set_worker_heartbeat() -> None:
    try:
        r = get_redis_client()
        r.set(_HEARTBEAT_KEY, "1", ex=settings.WORKER_HEARTBEAT_TTL_SECONDS)
    except Exception:
        pass
