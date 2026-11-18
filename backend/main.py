"""云东AI购 · 应用入口。启动：cd backend && uvicorn main:app --reload --port 8000"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import Base, engine
from app.router import product, trade, user

logger = logging.getLogger("uvicorn.error")

# 获取项目根目录：backend/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

TAGS_METADATA = [
    {"name": "系统", "description": "健康检查 / 接口文档"},
    {"name": "用户", "description": "注册、登录、当前用户"},
    {"name": "商品", "description": "分类树、商品列表与详情"},
    {"name": "交易", "description": "购物车、地址、订单、钱包"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 有 MySQL 时优先用 database/init.sql；这里兜底，SQLite 演示也能直接跑
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # noqa: BLE001 - 建表失败不阻塞启动，交给运维排查
        logger.warning("自动建表失败（%s），请先执行 database/init.sql", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="自营 B2C 商城 · 前后端分离 · 接口契约见本页",
    openapi_tags=TAGS_METADATA,
    docs_url=None,  # 关掉默认 CDN 版文档，改用下面的本地资源版本
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["系统"], summary="健康检查")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/docs", include_in_schema=False)
def api_docs():
    """在线接口文档：优先用本地 swagger 资源，没有则回退 CDN。"""
    kwargs = {"openapi_url": app.openapi_url, "title": f"{settings.app_name}接口文档"}
    local_js = os.path.join(STATIC_DIR, "swagger", "swagger-ui-bundle.js")
    if os.path.isfile(local_js):
        kwargs.update(
            swagger_js_url="/static/swagger/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger/swagger-ui.css",
        )
    return get_swagger_ui_html(**kwargs)


app.include_router(user.router, prefix=settings.api_prefix)
app.include_router(product.router, prefix=settings.api_prefix)
app.include_router(trade.router, prefix=settings.api_prefix)

# swagger 本地资源（离线可用）
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 前端静态资源必须最后挂载：它是 catch-all，前面接口都匹配不上才交给前端
frontend_dir = os.path.normpath(os.path.join(BASE_DIR, settings.frontend_dir))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
