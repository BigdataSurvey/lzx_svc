# encoding: utf-8
from fastapi import APIRouter
from app.core.responses import ApiResponse, success
from app.infra.http_client import get

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/1 下午3:02
@desc: HTTP 客户端使用示例路由，演示通过封装的 http_client 调用第三方接口获取 IP 信息。
"""

router = APIRouter(tags=["demo-http"])
@router.get("/demo/http/ip", response_model=ApiResponse)
async def get_public_ip():
    """
    调用 httpbin.org/ip，返回当前出口 IP 信息。
    如果服务器不能访问外网，这个接口会报错，仅作为 http_client 演示。
    """
    resp = await get("https://httpbin.org/ip")
    data = resp.json()
    return success(data)
