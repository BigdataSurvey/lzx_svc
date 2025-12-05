# encoding: utf-8
from typing import AsyncGenerator
import warnings

# ============================================================
# [防御性配置] 屏蔽 Paramiko/Cryptography 的 TripleDES 警告
# ============================================================
warnings.filterwarnings("ignore", module="cryptography")
warnings.filterwarnings("ignore", module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*")

from loguru import logger
from app.infra.ssh_tunnel import get_tunneled_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 基于 SQLAlchemy 的 MySQL 异步客户端封装，提供 ORM Base 和 get_db 依赖注入。
"""

class Base(DeclarativeBase):
    """ORM 基类，后面模型都继承这个"""
    pass

# 初始化全局 Engine
engine = create_async_engine(
    get_tunneled_url(settings.mysql.main_url),
    echo=settings.logging.show_sql,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入使用：
        async def api(db: AsyncSession = Depends(get_db)):
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            logger.exception("DB session error")
            raise

async def close_mysql() -> None:
    """
    关闭 MySQL 连接池，供 lifespan shutdown 使用。
    """
    logger.info("[mysql] disposing engine...")
    await engine.dispose()