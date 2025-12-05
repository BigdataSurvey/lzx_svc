# encoding: utf-8
import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings
from app.core.responses import ApiResponse, success
from app.infra.llm_client import get_dashscope_vision_client

router = APIRouter(tags=["idcard-analyzer"])

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/01
@desc: 身份证图片信息抽取接口，使用 DashScope 图像模型，将身份证图片解析为结构化 JSON。
"""

class ImageUrl(BaseModel):
    image_url: str


SYSTEM_PROMPT = """\
Role: 中国居民身份证信息抽取器
Description:
  你接收一张中国居民身份证的图片（可能是正面、反面或正反两张合成在一张图里），需要从中尽可能准确地抽取关键信息，并按 JSON 格式输出。

Goals:
1. 识别并抽取以下字段（能看到就填，没看到就为空字符串）：
   - name: 姓名
   - id_number: 公民身份证号码
   - gender: 性别（男/女）
   - ethnicity: 民族
   - birth_date: 出生日期，建议格式 YYYY-MM-DD
   - address: 住址
   - issuing_authority: 签发机关
   - valid_from: 证件有效期起始日期，建议格式 YYYY-MM-DD
   - valid_to: 证件有效期截止日期，建议格式 YYYY-MM-DD 或 “长期”

Constrains:
1. 必须尽可能准确地从图片中识别文字内容。
2. 必须输出合法的 JSON，字段名固定为上面列出的英文 key。
3. 如果某个字段在图片中看不到或无法识别，请使用空字符串 "" 作为值。
4. 严格禁止输出任何 JSON 以外的说明性文字，不要加自然语言解释。
5. 不要输出多余的字段。
{
  "image_url": "https://q5.itc.cn/q_70/images03/20250208/4d1b80ce0c9a4ec2840acf4c79b3c363.jpeg"
}
Output 示例:
{
  "name": "张三",
  "id_number": "110101199003150012",
  "gender": "男",
  "ethnicity": "汉",
  "birth_date": "1990-03-15",
  "address": "北京市东城区XX路XX号",
  "issuing_authority": "北京市公安局东城区分局",
  "valid_from": "2010-05-01",
  "valid_to": "长期"
}
"""


@router.post("/img/idcard/analyze", response_model=ApiResponse)
async def analyze_idcard(body: ImageUrl):
    """
    根据身份证图片抽取关键信息，返回结构化 JSON。
    入参：image_url
    出参：data 为一个 JSON 对象，字段见 SYSTEM_PROMPT 中定义。
    """
    logger.info(f"[IdCardAnalyzer] image_url={body.image_url}")

    client = get_dashscope_vision_client()
    user_prompt = "请根据 system 的说明，从这张身份证图片中抽取信息并返回 JSON。"

    try:
        raw_answer: str = await client.analyze_image(
            image_url=body.image_url,
            prompt=user_prompt,
            user=settings.llm.default_user,
            system_prompt=SYSTEM_PROMPT,
        )
        logger.info(f"[IdCardAnalyzer] raw_answer={raw_answer!r}")

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
            logger.warning(f"[IdCardAnalyzer] JSON parse failed: {e} | text={text!r}")
            raise HTTPException(status_code=400, detail=f"JSON 解析失败: {str(e)}")

        return success(data)
    except HTTPException:
        # 已经是 HTTPException，直接抛出
        raise
    except Exception as e:
        logger.exception("[IdCardAnalyzer] unexpected error")
        raise HTTPException(status_code=500, detail=str(e))
