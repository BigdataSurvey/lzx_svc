# encoding: utf-8
import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings
from app.core.responses import ApiResponse, success
from app.infra.llm_client import get_dashscope_vision_client

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28
@desc: 图片内容解析专用路由，使用 DashScope 图像模型按固定 system prompt 提取文字信息并输出 JSON。
        为营业执照定制接口
"""

router = APIRouter(tags=["img-analyzer"])


class ImageUrl(BaseModel):
    image_url: str


SYSTEM_PROMPT = """\
Role: 图片信息提取器
Description: 专门用于从图片中提取文字信息，包括姓名和其他文字内容，并输出为 JSON 格式。
Goals:
1. 识别图片中的所有文字内容
2. 提取并识别其中的姓名
3. 输出 JSON 格式的结果

Constrains:
1. 必须尽可能准确地识别图片中的文字
2. 识别结果需包括姓名和所有文字内容
3. 输出格式需符合 JSON 规范
4. 只输出 JSON，不输出其他说明、解释或多余文字

Output 示例:
{
    "name": "John Doe",
    "text": "This is a sample text containing John Doe's name and additional information."
}
"""

## 为“营业执照识别”定制的业务接口
@router.post("/img/analyze", response_model=ApiResponse)
async def analyze_image(body: ImageUrl):
    """
    解析图片中的文字信息：
      - 入参：image_url
      - 输出：JSON，其中包含 name 和 text 两个字段
    """
    logger.info(f"[ImgAnalyzer] image_url={body.image_url}")

    client = get_dashscope_vision_client()

    # 给 user 的自然语言指令，真正的约束写在 SYSTEM_PROMPT
    user_prompt = "请根据 system 的说明，从图片中提取文字并返回 JSON。"

    try:
        raw_answer: str = await client.analyze_image(
            image_url=body.image_url,
            prompt=user_prompt,
            user=settings.llm.default_user,
            system_prompt=SYSTEM_PROMPT,
        )
        logger.info(f"[ImgAnalyzer] raw_answer={raw_answer!r}")

        # 兼容 ```json ... ``` 或 ``` 开头的情况
        text = raw_answer.strip()

        if text.startswith("```"):
            # 去掉首尾 ``` 包裹
            text = text.strip("`").strip()
            # 可能形如 "json\n{...}"
            if text.lower().startswith("json"):
                text = text[4:].lstrip("\n").strip()

        try:
            data: Dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"[ImgAnalyzer] JSON parse failed: {e} | text={text!r}")
            raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")

        return success(data)
    except HTTPException:
        # 已经是 HTTPException，直接抛出
        raise
    except Exception as e:
        logger.exception("[ImgAnalyzer] unexpected error")
        raise HTTPException(status_code=500, detail=str(e))
