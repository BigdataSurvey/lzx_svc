# encoding: utf-8

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午3:00
@desc: 通用 Pydantic Schema 定义（如分页结构等），供各业务模块复用。
"""

T = TypeVar("T")


class PageMeta(BaseModel):
    """
    分页元信息：
      - page: 当前页（从 1 开始）
      - size: 每页条数
      - total: 总记录数
    """

    page: int = Field(..., ge=1, description="当前页码，从 1 开始")
    size: int = Field(..., ge=1, description="每页大小")
    total: int = Field(..., ge=0, description="总记录数")


class PageResult(Generic[T], BaseModel):
    """
    通用分页返回数据结构：
      - meta: 分页元信息
      - items: 当前页的数据列表
    """

    meta: PageMeta
    items: List[T]
