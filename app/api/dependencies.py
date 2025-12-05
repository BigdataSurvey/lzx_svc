# encoding: utf-8

from typing import Any

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.infra.mysql import get_db as get_db  # 直接复用原来的 get_db 依赖
import app.infra.redis_client as redis_client
import app.infra.mongo_client as mongo_client
from app.infra.llm_client import (
    get_llm_client,
    get_dashscope_vision_client,
)
from app.infra.http_client import get_http_client

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午3:20
@desc: 统一集中定义 FastAPI 依赖函数（dependencies），供各路由模块通过 Depends 引用。
"""


# ========= 配置相关 =========


def get_app_settings() -> Settings:
    """
    获取全局配置 Settings。
    """
    return get_settings()


# ========= 数据库相关 =========
# 这里直接使用 from app.infra.mysql import get_db as get_db
# 不再自己包装一层，保持其为 async generator，让 FastAPI 正确管理会话的创建和关闭


# ========= Redis / Mongo / HTTP / LLM 等统一出入口 =========


def get_redis():
    """
    获取 Redis 客户端。

    注意：这里使用懒加载 + 兜底写法，避免因函数名不一致导致项目无法启动。
    你可以在 app.infra.redis_client 中实现任意一个：
      - get_redis_client()
      - get_redis()
    之后这里会自动调用。
    """
    fn = getattr(redis_client, "get_redis_client", None) or getattr(
        redis_client, "get_redis", None
    )
    if fn is None:
        raise RuntimeError(
            "redis_client 中未找到 get_redis_client 或 get_redis，请实现后再使用 get_redis 依赖"
        )
    return fn()


def get_mongo():
    """
    获取 MongoDB 客户端。逻辑与 get_redis 相同，使用懒加载方式。
    """
    fn = getattr(mongo_client, "get_mongo_client", None) or getattr(
        mongo_client, "get_mongo", None
    )
    if fn is None:
        raise RuntimeError(
            "mongo_client 中未找到 get_mongo_client 或 get_mongo，请实现后再使用 get_mongo 依赖"
        )
    return fn()


def get_llm():
    """
    获取「默认」的大模型客户端（由 settings.llm.provider 决定）。
    """
    return get_llm_client()


def get_vision_llm():
    """
    获取 DashScope 图像模型客户端（用于图像理解等场景）。
    """
    return get_dashscope_vision_client()


def get_http():
    """
    获取全局 HTTP 客户端封装（httpx.AsyncClient）。
    """
    return get_http_client()
