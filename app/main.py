"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: FastAPI 服务入口模块，供 uvicorn 加载 app 实例。
"""
# ============================================================
# [Fix] 屏蔽 Paramiko < 3.0 产生的 CryptographyDeprecationWarning
# 必须放在任何 import app 之前执行，否则拦截无效
import warnings
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except ImportError:
    pass
# ============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import BizException, ErrorCode
from app.core.logging import configure_logging, log_startup_banner
from app.core.responses import fail
from app.core.middlewares import RequestLogMiddleware
from app.api import api_router

# 引入所有基础设施的资源释放钩子
from app.infra.ssh_tunnel import close_all_tunnels
from app.infra.mysql import close_mysql
from app.infra.doris import close_doris
from app.infra.redis_client import close_redis
from app.infra.mongo_client import close_mongo
from app.infra.es_client import close_es


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理：启动初始化 -> 运行 -> 关闭清理
    """
    # 1. 启动阶段
    configure_logging()
    log_startup_banner()
    logger.info("应用启动中...")
    logger.info(f"App starting... env={settings.env.value}")

    yield

    # 2. 关闭阶段：统一释放所有资源
    logger.info("应用关闭中，正在释放资源...")

    # 数据库与中间件 (异步/同步混合处理)
    await close_mysql()
    close_doris()  # Doris 使用的是同步引擎
    await close_redis()
    close_mongo()  # Mongo 使用的是同步客户端
    await close_es()

    # 最后关闭 SSH 隧道，确保所有数据包已发送
    close_all_tunnels()

    logger.info("App shutting down... 资源释放完毕，再见！")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # 1. 注册全局中间件
    app.add_middleware(RequestLogMiddleware)

    # 2. CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. 全局异常处理
    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        logger.warning(
            f"BizException path={request.url.path} code={exc.code} msg={exc.msg}"
        )
        return JSONResponse(
            status_code=200,
            content=fail(code=int(exc.code), msg=exc.msg, data=exc.data).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            f"ValidationError path={request.url.path} errors={exc.errors()}"
        )
        return JSONResponse(
            status_code=422,
            content=fail(
                code=ErrorCode.VALIDATION_ERROR,
                msg="参数校验失败",
                data=exc.errors(),
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(
            f"HTTPException path={request.url.path} status={exc.status_code} detail={exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(
                code=exc.status_code,
                msg=str(exc.detail),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception path={request.url.path}")
        return JSONResponse(
            status_code=500,
            content=fail(
                code=ErrorCode.INTERNAL_ERROR,
                msg="服务内部错误",
            ).model_dump(),
        )

    # 4. 注册路由
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)