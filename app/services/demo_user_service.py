# encoding: utf-8

from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.demo_user import DemoUser
from app.schemas.demo_user import DemoUserCreate, DemoUserUpdate

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午5:10
@desc: demo_user 业务逻辑层，封装对 DemoUser 的增删改查操作。
"""


async def list_users(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 20,
) -> List[DemoUser]:
    stmt = (
        select(DemoUser)
        .order_by(DemoUser.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user(
    db: AsyncSession,
    user_id: int,
) -> Optional[DemoUser]:
    stmt = select(DemoUser).where(DemoUser.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    data: DemoUserCreate,
) -> DemoUser:
    obj = DemoUser(name=data.name, age=data.age)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_user(
    db: AsyncSession,
    user_id: int,
    data: DemoUserUpdate,
) -> Optional[DemoUser]:
    stmt = (
        update(DemoUser)
        .where(DemoUser.id == user_id)
        .values(
            **{k: v for k, v in data.dict(exclude_unset=True).items()}
        )
        .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
    await db.commit()
    # 再查一遍最新数据返回
    return await get_user(db, user_id)


async def delete_user(
    db: AsyncSession,
    user_id: int,
) -> None:
    stmt = delete(DemoUser).where(DemoUser.id == user_id)
    await db.execute(stmt)
    await db.commit()
