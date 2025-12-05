"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28
@desc: 统一大模型访问客户端封装，支持 Dify、阿里云百炼 DashScope 文本/图像和火山引擎 Ark。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from loguru import logger

from app.core.config import settings
from app.core.exceptions import BizException, ErrorCode
from app.infra.http_client import post


class BaseLlmClient(ABC):
    @abstractmethod
    async def chat(self, prompt: str, user: Optional[str] = None) -> str:
        """
        简单对话接口：输入一个 prompt，返回模型的文本回复。
        """
        raise NotImplementedError


# ==================== Dify 实现（暂时不用，但保留） ====================


class DifyLlmClient(BaseLlmClient):
    """
    Dify 官方 HTTP API：/v1/chat-messages
    """

    def __init__(self, endpoint: str, api_key: str, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def chat(self, prompt: str, user: Optional[str] = None) -> str:
        if not self.endpoint or not self.api_key:
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(Dify) 未配置 endpoint 或 api_key",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "inputs": {"prompt": prompt},
            "response_mode": "blocking",
            "user": user or settings.llm.default_user,
        }

        logger.info(f"LLM[Dify] chat request | user={payload['user']}")

        resp = await post(
            self.endpoint,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        data = resp.json()

        answer = data.get("answer") or data.get("output_text")
        if not answer:
            logger.warning(f"LLM[Dify] empty answer | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(Dify) 未返回有效的 answer 字段",
            )
        return answer


# ==================== DashScope 文本模型实现 ====================


class DashScopeLlmClient(BaseLlmClient):
    """
    阿里云百炼 DashScope 的 OpenAI 兼容 chat/completions 接口（文本模型）。
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.endpoint = (
            endpoint.rstrip("/")
            if endpoint
            else "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        )
        self.api_key = api_key
        self.model = model or "qwen-plus"
        self.timeout = timeout

    async def chat(self, prompt: str, user: Optional[str] = None) -> str:
        if not self.api_key:
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(DashScope) 未配置 api_key",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "user": user or settings.llm.default_user,
        }

        logger.info(
            f"LLM[DashScope] chat request | model={self.model} "
            f"user={payload['user']}"
        )

        resp = await post(
            self.endpoint,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        data = resp.json()

        # OpenAI 兼容格式
        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = message.get("content") or ""
        except Exception:
            logger.warning(f"LLM[DashScope] unexpected response | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(DashScope) 返回格式异常",
            )

        if not content:
            logger.warning(f"LLM[DashScope] empty content | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(DashScope) 未返回有效的 content",
            )

        return content


# ==================== DashScope 图像 / 多模态实现 ====================


class DashScopeVisionClient:
    """
    DashScope 图像模型（例如 qwen-vl-max-latest），使用 OpenAI 兼容多模态格式：
      messages: [
        {
          "role": "system",
          "content": [{"type": "text", "text": "system prompt..."}]
        },
        {
          "role": "user",
          "content": [
            {"type": "image_url", "image_url": {"url": "xxx"}},
            {"type": "text", "text": "请描述这张图片"}
          ]
        }
      ]
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str = "qwen-vl-max-latest",
        timeout: float = 60.0,
    ):
        self.endpoint = (
            endpoint.rstrip("/")
            if endpoint
            else "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        )
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        user: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        if not self.api_key:
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "DashScope 图像模型未配置 api_key",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 构造多模态 messages：可选 system + user(image + text)
        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt,
                        }
                    ],
                }
            )

        user_content = [
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
            {
                "type": "text",
                "text": prompt,
            },
        ]

        messages.append(
            {
                "role": "user",
                "content": user_content,
            }
        )

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "user": user or settings.llm.default_user,
        }

        logger.info(
            f"LLM[DashScope-Vision] request | model={self.model} "
            f"user={payload['user']}"
        )

        resp = await post(
            self.endpoint,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        data = resp.json()

        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = message.get("content") or ""
        except Exception:
            logger.warning(f"LLM[DashScope-Vision] unexpected response | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "DashScope 图像模型返回格式异常",
            )

        if not content:
            logger.warning(f"LLM[DashScope-Vision] empty content | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "DashScope 图像模型未返回有效内容",
            )

        return content


# ==================== 火山引擎 Ark 实现 ====================


class VolcEngineLlmClient(BaseLlmClient):
    """
    火山引擎 Ark OpenAI 兼容 chat/completions 接口。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        timeout: float = 180.0,
    ):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    async def chat(self, prompt: str, user: Optional[str] = None) -> str:
        if not self.api_key or not self.model:
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(VolcEngine) 未配置 api_key 或 model",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "user": user or settings.llm.default_user,
        }

        logger.info(
            f"LLM[VolcEngine] chat request | model={self.model} "
            f"user={payload['user']}"
        )

        resp = await post(
            self.url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        data = resp.json()

        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = message.get("content") or ""
        except Exception:
            logger.warning(f"LLM[VolcEngine] unexpected response | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(VolcEngine) 返回格式异常",
            )

        if not content:
            logger.warning(f"LLM[VolcEngine] empty content | raw={data}")
            raise BizException(
                ErrorCode.BUSINESS_ERROR,
                "LLM(VolcEngine) 未返回有效的 content",
            )

        return content


# ==================== 工厂方法 ====================

_llm_clients: Dict[str, BaseLlmClient] = {}
_vision_client: Optional[DashScopeVisionClient] = None


def get_llm_client(provider: Optional[str] = None) -> BaseLlmClient:
    """
    根据 provider 或 settings.llm.provider 返回对应的 LLM 客户端实例。
    支持：
      - dify
      - dashscope
      - volcengine / volc
    """
    p = (provider or settings.llm.provider).lower()

    if p in _llm_clients:
        return _llm_clients[p]

    if p == "dify":
        client = DifyLlmClient(
            endpoint=settings.llm.endpoint,
            api_key=settings.llm.api_key,
            timeout=settings.llm.timeout,
        )
        logger.info("Init LLM client: Dify")
        _llm_clients[p] = client
        return client

    if p == "dashscope":
        api_key = settings.llm.api_key or settings.llm.dashscope_backup_api_key
        client = DashScopeLlmClient(
            endpoint=settings.llm.endpoint,
            api_key=api_key,
            model=settings.llm.model,
            timeout=settings.llm.timeout,
        )
        logger.info("Init LLM client: DashScope")
        _llm_clients[p] = client
        return client

    if p in ("volcengine", "volc"):
        client = VolcEngineLlmClient(
            base_url=settings.llm.volc_base_url,
            api_key=settings.llm.volc_api_key,
            model=settings.llm.volc_model,
            temperature=settings.llm.volc_temperature,
            timeout=settings.llm.volc_timeout,
        )
        logger.info("Init LLM client: VolcEngine")
        _llm_clients[p] = client
        return client

    raise BizException(
        ErrorCode.BUSINESS_ERROR,
        f"暂不支持的 LLM provider: {settings.llm.provider}",
    )


def get_dashscope_vision_client() -> DashScopeVisionClient:
    """
    获取 DashScope 图像模型客户端实例。
    使用 dashscope_vision_api_key 优先，其次 api_key，再次 backup_api_key。
    """
    global _vision_client
    if _vision_client is not None:
        return _vision_client

    api_key = (
        settings.llm.dashscope_vision_api_key
        or settings.llm.api_key
        or settings.llm.dashscope_backup_api_key
    )
    model = settings.llm.dashscope_vision_model

    _vision_client = DashScopeVisionClient(
        endpoint=settings.llm.endpoint,
        api_key=api_key,
        model=model,
        timeout=settings.llm.timeout,
    )
    logger.info("Init LLM client: DashScope-Vision")
    return _vision_client
