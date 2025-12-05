# encoding: utf-8
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午3:20
@desc: 全局中间件模块，负责请求全链路追踪 ID 生成、访问日志记录及耗时统计。
       替代 main.py 中散乱的日志拦截逻辑。
"""


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. 生成或获取 Request ID (全链路追踪核心)
        # 如果上游(如Nginx/网关)传了 X-Request-ID 则沿用，否则生成新的 UUID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 2. 记录开始时间
        start_time = time.perf_counter()

        # 3. 将 req_id 注入到当前请求上下文 (可选，如果需要 loguru bind 可在此扩展)
        # 此处为了简单展示，直接在 log 字符串体现

        try:
            response: Response = await call_next(request)
        except Exception as e:
            # 捕获未被 ExceptionHandler 处理的异常（极少情况）
            cost = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed | req_id={request_id} | path={request.url.path} | cost={cost:.2f}ms | error={e}")
            raise e

        # 4. 计算耗时
        cost = (time.perf_counter() - start_time) * 1000

        # 5. 打印结构化日志 (忽略健康检查等噪音)
        if not request.url.path.startswith("/.well-known") and "/health" not in request.url.path:
            logger.info(
                f"{request.method} {request.url.path} | "
                f"status={response.status_code} | "
                f"req_id={request_id} | "
                f"cost={cost:.2f}ms"
            )

        # 6. 将 Request ID 返回给客户端 Response Header，方便联调排查
        response.headers["X-Request-ID"] = request_id

        return response