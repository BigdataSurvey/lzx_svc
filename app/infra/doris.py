# encoding: utf-8
from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Generator, Optional

# ============================================================
# [防御性配置] 屏蔽 Paramiko/Cryptography 的 TripleDES 警告
# ============================================================
warnings.filterwarnings("ignore", module="cryptography")
warnings.filterwarnings("ignore", module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*")

import pymysql
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infra.ssh_tunnel import get_tunneled_url

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: Doris (基于 MySQL 协议) 客户端封装。
       已集成 SSH 隧道自动穿透与连接池管理。
"""

# 全局 Doris Engine 与 Session 工厂
_doris_engine: Optional[Engine] = None
_DorisSessionLocal: Optional[sessionmaker] = None


def init_doris() -> None:
    """
    初始化 Doris 同步 SQLAlchemy Engine 与 Session 工厂。
    """
    global _doris_engine, _DorisSessionLocal

    if _doris_engine is not None and _DorisSessionLocal is not None:
        return

    raw_url = settings.doris.url
    if not raw_url:
        # 如果配置为空，只打印警告，不阻断启动（可能该环境不需要 Doris）
        logger.warning("DORIS__URL 未配置，跳过初始化")
        return

    # 1. SSH 隧道处理：如果开启，自动映射到本地端口
    effective_url = get_tunneled_url(raw_url)
    logger.info(f"[doris] effective url = {effective_url!r}")

    # 2. 解析 URL 参数供 pymysql 使用
    url = make_url(effective_url)
    host = url.host or "127.0.0.1"
    port = url.port or 9030
    user = url.username or ""
    password = url.password or ""
    database = url.database or ""
    charset = "utf8mb4"
    if hasattr(url, "query") and isinstance(url.query, dict):
        charset = url.query.get("charset", charset)

    def _create_pymysql_connection():
        """自定义连接工厂，确保使用 pymysql 且参数正确"""
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            autocommit=False, # 交给 SQLAlchemy 管理事务
        )
        return conn

    # 3. 创建引擎
    _doris_engine = create_engine(
        "mysql+pymysql://",
        creator=_create_pymysql_connection,
        pool_pre_ping=True,
        echo=settings.logging.show_sql,
        pool_size=10,
        max_overflow=20,
    )

    _DorisSessionLocal = sessionmaker(
        bind=_doris_engine,
        autoflush=False,
        autocommit=False,
    )

    logger.info("[doris] engine & session factory initialized")


@contextmanager
def get_doris_session() -> Generator[Session, None, None]:
    """
    获取 Doris Session 的上下文管理器。
    """
    if _doris_engine is None or _DorisSessionLocal is None:
        init_doris()

    if _DorisSessionLocal is None:
        raise RuntimeError("Doris 初始化失败或未配置，无法获取会话")

    session: Session = _DorisSessionLocal()
    try:
        yield session
    finally:
        session.close()


def close_doris() -> None:
    """
    [新增] 优雅关闭 Doris 连接池，供 lifespan 调用。
    """
    global _doris_engine
    if _doris_engine:
        logger.info("[doris] disposing engine...")
        _doris_engine.dispose()
        _doris_engine = None