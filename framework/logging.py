import logging
import sys
from typing import Optional

from framework.config import AppConfig


def configure_logging(level: str = "info", format_string: Optional[str] = None) -> None:
    """配置应用程序日志"""
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(message)s"
        )

    log_level = getattr(logging, level.upper(), logging.INFO)

    # 配置根日志记录器
    logging.basicConfig(
        level=log_level,
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )