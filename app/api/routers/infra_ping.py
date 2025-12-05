from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.responses import ApiResponse, success
from app.infra.mysql import get_db
from app.infra.redis_client import get_redis
from app.infra.mongo_client import get_mongo_primary
from app.infra.doris import get_doris_session
from app.infra.es_client import get_es
from app.infra.qiniu_client import get_qiniu_client

...

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 基础设施连通性检测路由，聚合 MySQL/Redis/Mongo/Doris/ES/七牛等 ping 接口。
"""

router = APIRouter(tags=["infra"])


@router.get("/infra/ping/mysql", response_model=ApiResponse)
async def ping_mysql(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return success({"ok": True})


@router.get("/infra/ping/redis", response_model=ApiResponse)
async def ping_redis(r=Depends(get_redis)):
    pong = await r.ping()
    return success({"pong": pong})


@router.get("/infra/ping/mongo", response_model=ApiResponse)
def ping_mongo(db=Depends(get_mongo_primary)):
    """
    同步访问 Mongo；FastAPI 会在内部用线程池执行这个函数
    """
    res = db.command("ping")
    return success({"ok": res.get("ok", 0) == 1})


@router.get("/infra/ping/doris", response_model=ApiResponse)
async def ping_doris():
    from sqlalchemy import text

    ok = False
    with get_doris_session() as s:
        result = s.execute(text("SELECT 1"))
        ok = result.scalar() == 1
    return success({"ok": ok})


@router.get("/infra/ping/es", response_model=ApiResponse)
async def ping_es(es=Depends(get_es)):
    info = await es.info()
    return success({"cluster_name": info.get("cluster_name")})


@router.get("/infra/ping/qiniu", response_model=ApiResponse)
async def ping_qiniu():
    q = get_qiniu_client()
    token = q.get_upload_token("test-key")
    return success({"has_token": bool(token)})
