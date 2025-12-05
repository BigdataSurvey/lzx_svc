# encoding: utf-8
from typing import AsyncGenerator, Optional
import warnings

# ============================================================
# [防御性配置]
# ============================================================
warnings.filterwarnings("ignore", module="cryptography")
warnings.filterwarnings("ignore", module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*")

import redis.asyncio as redis
from loguru import logger
from app.core.config import settings
from app.infra.ssh_tunnel import get_tunneled_url

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: Redis 异步客户端封装。
       已升级：支持 SSH 隧道自动连接生产 Redis。
"""

_redis_client: Optional[redis.Redis] = None


def init_redis() -> None:
    """
    初始化 Redis 连接池（自动处理 SSH 隧道）。
    """
    global _redis_client

    if _redis_client is not None:
        return

    raw_url = settings.redis.url
    if not raw_url:
        logger.warning("REDIS__URL 未配置，跳过初始化")
        return

    # 1. SSH 隧道处理：如果需要，自动将 Redis 地址映射到本地
    effective_url = get_tunneled_url(raw_url)

    logger.info(f"[redis] init client, effective_url={effective_url!r}")

    # 2. 创建客户端
    _redis_client = redis.from_url(
        effective_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    FastAPI 依赖注入：
        async def api(r = Depends(get_redis_client)):
    """
    if _redis_client is None:
        init_redis()

    if _redis_client is None:
        raise RuntimeError("Redis 未配置或初始化失败")

    yield _redis_client


# 兼容旧代码的别名
get_redis = get_redis_client


async def close_redis() -> None:
    """
    [新增] 优雅关闭 Redis 连接池。
    """
    global _redis_client
    if _redis_client:
        logger.info("[redis] closing connection pool...")
        await _redis_client.close()
        _redis_client = None