import os
from dataclasses import dataclass
from dotenv import load_dotenv


# .env file path - adjust based on project structure in container
ENV_FILE_PREFIX = ".env"


@dataclass(frozen=True)
class AppConfig:
    environment: str
    port: int
    log_level: str

    # Redis配置（可选，如果不使用Redis可以不配置）
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str | None
    redis_timeout: int
    


def load_environment() -> str:
    env = os.getenv("ENVIRONMENT", "dev").lower()
    env_file = {
        "dev": f"{ENV_FILE_PREFIX}.dev",
        "test": f"{ENV_FILE_PREFIX}.test",
        "pro": f"{ENV_FILE_PREFIX}.pro",
    }.get(env)
    if not env_file:
        raise ValueError(f"Unsupported ENVIRONMENT={env!r}")

    # 不覆盖进程环境变量（更符合企业部署：以环境变量为准）
    load_dotenv(env_file, override=False)
    return env


def get_config() -> AppConfig:
    environment = load_environment()

    def _int(name: str, default: str) -> int:
        return int(os.getenv(name, default))

    log_level = os.getenv("LOG_LEVEL", "info").lower()
    return AppConfig(
        environment=environment,
        port=_int("PORT", "8080"),
        log_level=log_level,
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=_int("REDIS_PORT", "6379"),
        redis_db=_int("REDIS_DB", "0"),
        redis_password=os.getenv("REDIS_PASSWORD") or None,
        redis_timeout=_int("REDIS_TIMEOUT", "30"),
    )


def get_uvicorn_workers() -> int:
    """Get the number of uvicorn worker processes"""
    return int(os.getenv("UVICORN_WORKERS", "1"))