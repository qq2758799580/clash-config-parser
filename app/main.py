import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from framework.config import get_config
from framework.logging import configure_logging
from app.routers import clash

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    configure_logging(cfg.log_level)

    app.state.cfg = cfg
    
    logger.info("Clash配置解析器启动 env=%s", cfg.environment)
    try:
        yield
    finally:
        logger.info("Clash配置解析器停止")


app = FastAPI(
    title="Clash配置解析器",
    description="解析Clash配置文件并转换为节点链接",
    version="1.0.0",
    lifespan=lifespan
)

# 包含路由
app.include_router(clash.router, prefix="/api/clash", tags=["clash"])

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="frontend")