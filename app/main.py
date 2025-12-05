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

# Infra 资源释放 hook
from app.infra.ssh_tunnel import close_all_tunnels
from app.infra.mysql import close_mysql


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

    # 2. 关闭阶段
    logger.info("应用关闭中...")

    # 显式关闭数据库连接池
    await close_mysql()

    # 关闭所有 SSH 隧道
    close_all_tunnels()

    logger.info("App shutting down... Bye!")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # 1. 注册全局中间件 (注意顺序：先注册的后执行，RequestLog 最好在外层)
    app.add_middleware(RequestLogMiddleware)

    # 2. CORS 配置 (从 settings 读取)
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


# 入口实例
app = create_app()

if __name__ == "__main__":
    import uvicorn

    # 生产环境建议直接使用 uvicorn 命令启动，这里仅作为开发调试入口
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)