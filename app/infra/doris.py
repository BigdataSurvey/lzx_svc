from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

import pymysql
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infra.ssh_tunnel import get_tunneled_url

# 全局 Doris Engine 与 Session 工厂
_doris_engine: Optional[Engine] = None
_DorisSessionLocal: Optional[sessionmaker] = None


def init_doris() -> None:
    """
    初始化 Doris 同步 SQLAlchemy Engine 与 Session 工厂。

    关键点：
    - 使用 settings.doris.url 作为原始连接串；
    - 通过 get_tunneled_url 统一走 SSH 隧道，得到 127.0.0.1:本地端口；
    - 不让 SQLAlchemy 自己拼连接参数，而是用 creator，自行调用 pymysql.connect，
      调用方式等价于 app.infra.doris_ssh_test.py 中已经验证成功的逻辑。
    """
    global _doris_engine, _DorisSessionLocal

    # 已初始化直接返回
    if _doris_engine is not None and _DorisSessionLocal is not None:
        return

    raw_url = settings.doris.url
    if not raw_url:
        raise RuntimeError("DORIS__URL 未配置，无法初始化 Doris 连接")

    # 统一走 SSH：10.111.160.243:9030 -> 127.0.0.1:xxxx
    effective_url = get_tunneled_url(raw_url)
    logger.info(f"[doris] effective url = {effective_url!r}")

    # 解析 effective_url，拿到 host / port / user / password / db / charset
    url = make_url(effective_url)

    host = url.host or "127.0.0.1"
    port = url.port or 9030
    user = url.username or ""
    password = url.password or ""
    database = url.database or ""
    charset = "utf8mb4"
    if hasattr(url, "query") and isinstance(url.query, dict):
        charset = url.query.get("charset", charset)

    logger.info(
        "[doris] parsed url -> host=%r, port=%r, user=%r, db=%r, charset=%r",
        host,
        port,
        user,
        database,
        charset,
    )

    def _create_pymysql_connection():
        """
        由 SQLAlchemy Engine 调用的连接工厂。

        这里的实现等价于 app.infra.doris_ssh_test.py 中的 pymysql.connect，
        唯一差异是 autocommit=False，交给 SQLAlchemy 管理事务。
        """
        logger.info(
            "[doris] creating new pymysql connection: %r@%r:%r/%r",
            user,
            host,
            port,
            database,
        )
        # 这里是真正的 pymysql.connect 调用
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            autocommit=False,
        )
        return conn

    # 这里不再让 SQLAlchemy 根据 URL 解析 host/user/password，
    # 而是只告诉它：“这是 mysql+pymysql”，连接细节全由 creator 接管。
    _doris_engine = create_engine(
        "mysql+pymysql://",
        creator=_create_pymysql_connection,
        pool_pre_ping=True,
        echo=settings.logging.show_sql,
    )

    _DorisSessionLocal = sessionmaker(
        bind=_doris_engine,
        autoflush=False,
        autocommit=False,
    )

    logger.info("[doris] engine & session factory initialized (using custom pymysql creator)")


@contextmanager
def get_doris_session() -> Generator[Session, None, None]:
    """
    获取 Doris Session 的上下文管理器。

    用法示例：

        from sqlalchemy import text
        from app.infra.doris import get_doris_session

        with get_doris_session() as s:
            result = s.execute(text("SELECT 1"))
            print(result.scalar())

    会在 with 块结束后自动关闭 Session。
    """
    if _doris_engine is None or _DorisSessionLocal is None:
        init_doris()

    assert _DorisSessionLocal is not None
    session: Session = _DorisSessionLocal()
    try:
        yield session
    finally:
        session.close()
