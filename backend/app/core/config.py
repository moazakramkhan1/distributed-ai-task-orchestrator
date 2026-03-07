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

    model_config = {"env_file": ".env"}


settings = Settings()
