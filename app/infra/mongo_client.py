# encoding: utf-8
from typing import Optional
from loguru import logger
from pymongo import MongoClient
from app.core.config import settings
_primary_client: Optional[MongoClient] = None
_attend_client: Optional[MongoClient] = None

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 基于 pymongo 的 MongoDB 客户端封装，提供主库和考勤库的默认数据库访问。
"""

def init_mongo() -> None:
    """
    初始化 MongoClient（同步版本）
    """
    global _primary_client, _attend_client

    if settings.mongo.primary_uri and _primary_client is None:
        logger.info("Init Mongo primary client")
        _primary_client = MongoClient(settings.mongo.primary_uri)

    if settings.mongo.attendence_uri and _attend_client is None:
        logger.info("Init Mongo attendence client")
        _attend_client = MongoClient(settings.mongo.attendence_uri)


def get_mongo_primary():
    """
    FastAPI 依赖注入可以直接用这个函数：
        def api(db = Depends(get_mongo_primary)):
    返回的是默认数据库对象：pymongo.database.Database
    """
    if _primary_client is None:
        init_mongo()
    assert _primary_client is not None
    return _primary_client.get_default_database()


def get_mongo_attendence():
    if _attend_client is None:
        init_mongo()
    assert _attend_client is not None
    return _attend_client.get_default_database()
