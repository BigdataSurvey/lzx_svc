# encoding: utf-8

from fastapi import APIRouter

from app.api.routers import (
    health,
    http_demo,
    infra_ping,
    llm_demo,
    img_analyzer,
    idcard_analyzer,
    demo_user,
)

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午3:30
@desc: 聚合所有 API 路由，统一在 main.py 中挂载。
"""

api_router = APIRouter()

# 保持各 router 内部自己的 path 设计，
# 在 main.py 中统一加上 settings.api_prefix（例如 /api）
api_router.include_router(health.router)
api_router.include_router(infra_ping.router)
api_router.include_router(http_demo.router)
api_router.include_router(llm_demo.router)
api_router.include_router(img_analyzer.router)
api_router.include_router(idcard_analyzer.router)
# api_router.include_router(demo_user.router)
