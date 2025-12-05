# encoding: utf-8
from typing import AsyncGenerator
import redis.asyncio as redis
from loguru import logger
from app.core.config import settings
_redis: redis.Redis | None = None

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: Redis 异步客户端封装，负责根据配置初始化连接并通过依赖注入提供使用。
"""

def init_redis() -> None:
    global _redis
    if _redis is None:
        logger.info(f"Init redis client url={settings.redis.url}")
        _redis = redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
        )


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    if _redis is None:
        init_redis()
    assert _redis is not None
    yield _redis
