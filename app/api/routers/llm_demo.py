# encoding: utf-8
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.responses import ApiResponse, success
from app.infra.llm_client import (
    get_llm_client,
    get_dashscope_vision_client,
)

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28
@desc: LLM 客户端使用示例路由，提供文本与图像对话接口验证大模型调用链路。
"""

router = APIRouter(tags=["demo-llm"])

class ChatRequest(BaseModel):
    prompt: str
    user: Optional[str] = None


@router.post("/demo/llm/chat", response_model=ApiResponse)
async def llm_chat(body: ChatRequest):
    """
    使用默认 provider（当前为 DashScope 文本模型）进行简单对话。
    """
    client = get_llm_client()
    answer = await client.chat(body.prompt, user=body.user)
    return success({"answer": answer})


# ===== 火山引擎 文本模型测试 =====


@router.post("/demo/llm/chat/volc", response_model=ApiResponse)
async def llm_chat_volc(body: ChatRequest):
    """
    使用火山引擎 Ark 文本模型进行对话测试。
    """
    client = get_llm_client("volcengine")
    answer = await client.chat(body.prompt, user=body.user)
    return success({"answer": answer})


# ===== DashScope 图像模型测试 =====


class VisionChatRequest(BaseModel):
    image_url: str
    prompt: str = "请描述这张图片的内容"
    user: Optional[str] = None


# 底层调试 / 通用描述接口
@router.post("/demo/llm/vision/dashscope", response_model=ApiResponse)
async def llm_vision_dashscope(body: VisionChatRequest):
    """
    使用 DashScope 图像模型(qwen-vl-max-latest)对图片进行分析。
    目前接受一个公网可访问的 image_url。
    """
    client = get_dashscope_vision_client()
    answer = await client.analyze_image(
        image_url=body.image_url,
        prompt=body.prompt,
        user=body.user,
    )
    return success({"answer": answer})
