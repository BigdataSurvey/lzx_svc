# encoding: utf-8
from typing import AsyncGenerator
import warnings

# ============================================================
# [防御性配置] 屏蔽 Paramiko/Cryptography 的 TripleDES 警告
# 确保即使在非 main.py 入口（如单元测试或脚本）导入此模块时也清爽无警告
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

# =========================================================================
# 核心逻辑说明：
# 1. settings.mysql.main_url:
#    - 从配置文件(.env.prod)读取，此时是原始的 RDS 内网地址 (如 192.168.x.x)
#
# 2. get_tunneled_url(...):
#    - 这是一个智能函数，它会检查 Config 中的 SSH_TUNNEL__ENABLED
#    - 情况 A (Prod + SSH开启): 自动建立 SSH 隧道，返回映射后的地址 (127.0.0.1:xxxxx)
#    - 情况 B (Local / SSH关闭): 直接返回原始地址，不做任何改变
#
# 3. create_async_engine:
#    - 使用处理后的 URL 创建连接池，业务层完全无感知
# =========================================================================
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