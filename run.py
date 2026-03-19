import uvicorn

from framework.config import get_config, get_uvicorn_workers


def main() -> None:
    cfg = get_config()
    workers = get_uvicorn_workers()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=cfg.port,
        log_level=cfg.log_level,
        workers=workers,
    )


if __name__ == "__main__":
    main()