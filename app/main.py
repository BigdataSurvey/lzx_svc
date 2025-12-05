from contextlib import asynccontextmanager
from app.infra.ssh_tunnel import close_all_tunnels

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.core.config import settings
from app.core.exceptions import BizException, ErrorCode
from app.core.logging import configure_logging, log_startup_banner
from app.core.responses import fail
from app.api import api_router

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 构建 FastAPI 应用实例，配置生命周期、中间件、异常处理及路由注册。
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log_startup_banner()
    logger.info("应用启动中...")
    logger.info(f"App starting... env={settings.env.value}")

    try:
        yield
    finally:
        # 应用关闭前关掉所有 SSH 隧道
        close_all_tunnels()
        logger.info("应用关闭中...")
        logger.info("App shutting down...")


def create_app() -> FastAPI:
    # ✅ 先创建 FastAPI 实例
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 简单请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # 忽略某些探测类请求
        if request.url.path.startswith("/.well-known"):
            return await call_next(request)

        logger.info(f"{request.method} {request.url.path}")
        response = await call_next(request)
        return response

    # ===== 全局异常处理 =====

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        """
        业务主动抛出的异常：
            raise BizException(10001, "xxx 不存在")
        """
        logger.warning(
            f"BizException path={request.url.path} code={exc.code} msg={exc.msg}"
        )
        # HTTP 200 + 业务 code
        return JSONResponse(
            status_code=200,
            content=fail(code=int(exc.code), msg=exc.msg, data=exc.data).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        请求参数校验失败（FastAPI 自动抛的）
        """
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

    # ===== 注册路由（这里只保留一处）=====
    app.include_router(api_router, prefix=settings.api_prefix)
    return app



# ✅ 入口：给 uvicorn 用的 app 实例
app = create_app()
