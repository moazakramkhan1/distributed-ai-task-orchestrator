from typing import Optional

try:
    from kubernetes import client, config as k8s_config
    from kubernetes.client.exceptions import ApiException
    _K8S_AVAILABLE = True
except ImportError:
    _K8S_AVAILABLE = False

from app.core.config import settings


def _get_apps_v1() -> Optional[object]:
    if not _K8S_AVAILABLE:
        return None
    try:
        k8s_config.load_incluster_config()
    except Exception:
        try:
            k8s_config.load_kube_config()
        except Exception:
            return None
    return client.AppsV1Api()


def get_worker_deployment_status() -> dict:
    api = _get_apps_v1()
    if api is None:
        return _unavailable_response()

    try:
        dep = api.read_namespaced_deployment(
            name=settings.WORKER_DEPLOYMENT_NAME,
            namespace=settings.K8S_NAMESPACE,
        )
        spec = dep.spec
        status = dep.status
        desired = spec.replicas or 0
        available = status.available_replicas or 0
        ready = status.ready_replicas or 0
        return {
            "desired_replicas": desired,
            "available_replicas": available,
            "ready_replicas": ready,
            "min_replicas": settings.WORKER_MIN_REPLICAS,
            "max_replicas": settings.WORKER_MAX_REPLICAS,
            "k8s_available": True,
        }
    except Exception:
        return _unavailable_response()


def _unavailable_response() -> dict:
    return {
        "desired_replicas": None,
        "available_replicas": None,
        "ready_replicas": None,
        "min_replicas": settings.WORKER_MIN_REPLICAS,
        "max_replicas": settings.WORKER_MAX_REPLICAS,
        "k8s_available": False,
    }
