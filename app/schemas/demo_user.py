# encoding: utf-8

from datetime import datetime

from pydantic import BaseModel, Field

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午5:10
@desc: demo_user 相关的 Pydantic Schema 定义（入参 / 出参模型）。
"""


class DemoUserBase(BaseModel):
    name: str = Field(..., description="姓名")
    age: int | None = Field(None, description="年龄")


class DemoUserCreate(DemoUserBase):
    """
    创建用户时的入参模型。
    """
    pass


class DemoUserUpdate(BaseModel):
    """
    更新用户时的入参模型，全部字段可选。
    """

    name: str | None = Field(None, description="姓名")
    age: int | None = Field(None, description="年龄")


class DemoUserOut(DemoUserBase):
    """
    对外返回的用户信息。
    """

    id: int = Field(..., description="主键ID")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        orm_mode = True
