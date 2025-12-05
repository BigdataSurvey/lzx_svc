# encoding: utf-8
from typing import AsyncGenerator, List
from elasticsearch import AsyncElasticsearch
from loguru import logger
from app.core.config import settings
from app.core.exceptions import BizException, ErrorCode
_es: AsyncElasticsearch | None = None

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: Elasticsearch 异步客户端封装，从配置解析 hosts 并通过依赖注入提供 ES 实例。
"""

def _parse_hosts(raw: str) -> List[str]:
    """
    把配置里的 ES__HOSTS 字符串转成列表：
    "http://a:9200,http://b:9200" -> ["http://a:9200", "http://b:9200"]
    """
    if not raw:
        return []
    return [h.strip() for h in raw.split(",") if h.strip()]


def init_es() -> None:
    global _es
    hosts = _parse_hosts(settings.es.hosts)
    if not hosts:
        logger.warning("ES hosts not configured, skip init")
        return

    if _es is None:
        logger.info(f"Init ES client hosts={hosts}")
        _es = AsyncElasticsearch(hosts=hosts)


async def get_es() -> AsyncGenerator[AsyncElasticsearch, None]:
    """
    FastAPI 依赖注入：
        async def api(es = Depends(get_es)):
    """
    if _es is None:
        init_es()
    if _es is None:
        # 用业务异常抛出去，避免 assert 直接 500 没提示
        raise BizException(
            ErrorCode.BUSINESS_ERROR,
            "ES 未配置或初始化失败，请检查 ES__HOSTS",
        )
    yield _es
