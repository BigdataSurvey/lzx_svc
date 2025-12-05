# encoding: utf-8
from typing import AsyncGenerator, List, Optional
import warnings

# ============================================================
# [防御性配置]
# ============================================================
warnings.filterwarnings("ignore", module="cryptography")
warnings.filterwarnings("ignore", module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*")

from elasticsearch import AsyncElasticsearch
from loguru import logger
from app.core.config import settings
from app.core.exceptions import BizException, ErrorCode
from app.infra.ssh_tunnel import get_tunneled_url

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: Elasticsearch 异步客户端封装。
       已升级：支持多节点 SSH 隧道自动穿透。
"""

_es_client: Optional[AsyncElasticsearch] = None


def _parse_hosts(raw: List[str] | str) -> List[str]:
    """解析 ES hosts 配置，兼容字符串或列表"""
    if isinstance(raw, str):
        if not raw: return []
        return [h.strip() for h in raw.split(",") if h.strip()]
    return raw or []


def init_es() -> None:
    global _es_client

    if _es_client is not None:
        return

    raw_hosts = _parse_hosts(settings.es.hosts)
    if not raw_hosts:
        logger.warning("ES__HOSTS 未配置，跳过初始化")
        return

    # 关键升级：遍历所有 ES 节点，逐个建立/复用 SSH 隧道
    tunneled_hosts = []
    for host in raw_hosts:
        # 如果是 prod 环境，这里会自动把 http://10.x.x.x:9200 变成 http://127.0.0.1:xxxxx
        new_url = get_tunneled_url(host)
        tunneled_hosts.append(new_url)

    logger.info(f"[es] init client, hosts={tunneled_hosts}")
    _es_client = AsyncElasticsearch(hosts=tunneled_hosts)


async def get_es() -> AsyncGenerator[AsyncElasticsearch, None]:
    """
    FastAPI 依赖注入
    """
    if _es_client is None:
        init_es()

    if _es_client is None:
        raise BizException(
            ErrorCode.BUSINESS_ERROR,
            "ES 未配置或初始化失败，请检查 ES__HOSTS",
        )
    yield _es_client


async def close_es() -> None:
    """
    [新增] 优雅关闭 ES 连接。
    """
    global _es_client
    if _es_client:
        logger.info("[es] closing client...")
        await _es_client.close()
        _es_client = None