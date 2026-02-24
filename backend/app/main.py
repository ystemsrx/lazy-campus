import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import init_db

UPLOADS_DIR = Path(__file__).resolve().parents[1] / 'uploads'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

log_level_value = getattr(logging, settings.log_level, logging.INFO)
logging.basicConfig(
    level=log_level_value,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logging.getLogger().setLevel(log_level_value)
logging.getLogger('uvicorn').setLevel(log_level_value)
logging.getLogger('uvicorn.error').setLevel(log_level_value)
logging.getLogger('uvicorn.access').setLevel(log_level_value)

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
    logger.info('Starting app in env=%s, debug=%s, log_level=%s', settings.env, settings.debug, settings.log_level)
    init_db()


@app.get('/healthz')
def healthz() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(api_router, prefix=settings.api_v1_prefix)
# 挂载静态文件目录（用于头像等其他资源）；举报截图通过 /api/v1/uploads/reports/* 路由下发
app.mount('/uploads', StaticFiles(directory=str(UPLOADS_DIR)), name='uploads')
