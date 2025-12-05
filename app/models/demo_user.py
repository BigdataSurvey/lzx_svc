# encoding: utf-8
from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.infra.mysql import Base

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午5:10
@desc: demo_user 表的 ORM 模型定义，用于演示标准的 SQLAlchemy + FastAPI 使用方式。
"""

class DemoUser(Base):
    __tablename__ = "demo_user"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="年龄")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
