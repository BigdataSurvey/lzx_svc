# encoding: utf-8
from typing import Optional
import warnings

# ============================================================
# [防御性配置]
# ============================================================
warnings.filterwarnings("ignore", module="cryptography")
warnings.filterwarnings("ignore", module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*")

from loguru import logger
from pymongo import MongoClient
from app.core.config import settings
from app.infra.ssh_tunnel import get_tunneled_url

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 基于 pymongo 的 MongoDB 客户端封装。
       已升级：支持 SSH 隧道自动连接生产 MongoDB。
"""

_primary_client: Optional[MongoClient] = None
_attend_client: Optional[MongoClient] = None


def init_mongo() -> None:
    """
    初始化 MongoClient（同步版本），自动处理 SSH 隧道。
    """
    global _primary_client, _attend_client

    # 1. 初始化主库
    if settings.mongo.primary_uri and _primary_client is None:
        effective_uri = get_tunneled_url(settings.mongo.primary_uri)
        logger.info(f"[mongo] init primary client, uri={effective_uri!r}")
        _primary_client = MongoClient(effective_uri)

    # 2. 初始化考勤库
    if settings.mongo.attendence_uri and _attend_client is None:
        effective_uri = get_tunneled_url(settings.mongo.attendence_uri)
        logger.info(f"[mongo] init attendence client, uri={effective_uri!r}")
        _attend_client = MongoClient(effective_uri)


def get_mongo_primary():
    """
    FastAPI 依赖注入：返回默认数据库对象
    """
    if _primary_client is None:
        init_mongo()

    if _primary_client is None:
        raise RuntimeError("Mongo Primary URI 未配置")

    return _primary_client.get_default_database()


def get_mongo_attendence():
    if _attend_client is None:
        init_mongo()

    if _attend_client is None:
        raise RuntimeError("Mongo Attendence URI 未配置")

    return _attend_client.get_default_database()


def close_mongo() -> None:
    """
    [新增] 优雅关闭 Mongo 连接。
    """
    global _primary_client, _attend_client

    if _primary_client:
        logger.info("[mongo] closing primary client...")
        _primary_client.close()
        _primary_client = None

    if _attend_client:
        logger.info("[mongo] closing attendence client...")
        _attend_client.close()
        _attend_client = None