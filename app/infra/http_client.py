# encoding: utf-8
import asyncio
import time
from typing import Any, Optional
import httpx
from loguru import logger
from app.core.config import settings
_client: Optional[httpx.AsyncClient] = None

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28
@desc: 封装全局 httpx 异步客户端，提供带超时、重试和日志的 HTTP 请求能力。
"""

def get_http_client() -> httpx.AsyncClient:
    """
    获取全局 AsyncClient 单例。
    """
    global _client
    if _client is None:
        timeout = settings.http.timeout

        # 目前不直接在代码中传 proxies，避免不同版本 httpx 构造参数差异；
        # 如需代理，可通过系统环境变量 HTTP_PROXY / HTTPS_PROXY 配置。
        _client = httpx.AsyncClient(
            timeout=timeout,
        )
        logger.info(
            f"Init http client | timeout={timeout}s "
            f"retries={settings.http.max_retries}"
        )
    return _client


async def request(
    method: str,
    url: str,
    *,
    timeout: Optional[float] = None,
    retries: Optional[int] = None,
    **kwargs: Any,
) -> httpx.Response:
    """
    统一 HTTP 请求入口，带简单重试和日志。
    """
    client = get_http_client()
    timeout = timeout or settings.http.timeout
    retries = retries if retries is not None else settings.http.max_retries

    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            resp = await client.request(method, url, timeout=timeout, **kwargs)
            cost = (time.perf_counter() - start) * 1000
            logger.info(
                f"HTTP {method.upper()} {url} -> {resp.status_code} "
                f"({cost:.1f} ms)"
            )
            resp.raise_for_status()
            return resp
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            cost = (time.perf_counter() - start) * 1000
            logger.warning(
                f"HTTP {method.upper()} {url} failed on attempt {attempt + 1}/{retries + 1} "
                f"({cost:.1f} ms), error={exc!r}"
            )
            last_exc = exc
            if attempt >= retries:
                raise
            await asyncio.sleep(0.2 * (attempt + 1))  # 简单退避

    assert last_exc is not None
    raise last_exc


async def get(url: str, **kwargs: Any) -> httpx.Response:
    return await request("GET", url, **kwargs)


async def post(url: str, **kwargs: Any) -> httpx.Response:
    return await request("POST", url, **kwargs)
