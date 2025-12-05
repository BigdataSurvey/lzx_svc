import sys
import logging
from loguru import logger
from .config import settings

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 基于 loguru 的日志配置模块，统一初始化日志格式与等级。
"""
def configure_logging() -> None:
    """
    初始化 loguru 日志配置：
    - 根据 settings.logging.level 设置日志级别
    - 格式化输出时间、级别、模块、行号、消息
    - 控制 SQLAlchemy 的 SQL 日志级别（show_sql）
    """
    # 清理默认 handler
    logger.remove()

    log_level = settings.logging.level.upper()

    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )

    # 控制 SQLAlchemy 引擎日志
    sql_level = logging.INFO if settings.logging.show_sql else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sql_level)

    # 也可以顺带把 uvicorn 的 access 日志降一点噪
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def log_startup_banner() -> None:
    """
    打印启动信息：环境、日志级别、SQL 日志开关等。
    """
    logger.info(
        f"App starting | name={settings.app_name} "
        f"env={settings.env.value} debug={settings.debug} "
        f"log_level={settings.logging.level.upper()} "
        f"show_sql={settings.logging.show_sql}"
    )