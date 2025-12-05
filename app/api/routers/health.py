from fastapi import APIRouter
from app.core.responses import ApiResponse, success

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 健康检查路由模块，提供服务存活状态检测接口。
"""
router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse)
async def health():
    return success({"status": "ok"})
