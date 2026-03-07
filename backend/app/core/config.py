from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    SIMULATE_AI_FAILURE: bool = False

    WORKER_HEARTBEAT_TTL_SECONDS: int = 30

    CELERY_QUEUE_NAME: str = "celery"

    K8S_NAMESPACE: str = "ai-orchestrator"
    WORKER_DEPLOYMENT_NAME: str = "worker"
    WORKER_MIN_REPLICAS: int = 1
    WORKER_MAX_REPLICAS: int = 10

    model_config = {"env_file": ".env"}


settings = Settings()
