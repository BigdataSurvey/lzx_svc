# encoding: utf-8
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from qiniu import Auth
from app.core.config import settings

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 七牛云存储访问客户端封装，提供上传凭证生成和文件访问地址构建能力。
"""

@dataclass
class QiniuClient:
    access_key: str
    secret_key: str
    bucket: str
    domain: Optional[str] = None

    def __post_init__(self):
        self._auth = Auth(self.access_key, self.secret_key)

    def get_upload_token(self, key: str, expire: int = 3600) -> str:
        """
        生成上传凭证
        """
        return self._auth.upload_token(self.bucket, key, expire)

    def build_url(self, key: str) -> Optional[str]:
        if not self.domain:
            return None
        return f"{self.domain.rstrip('/')}/{key.lstrip('/')}"


_qiniu_client: QiniuClient | None = None


def get_qiniu_client() -> QiniuClient:
    global _qiniu_client
    if _qiniu_client is None:
        logger.info("Init Qiniu client")
        _qiniu_client = QiniuClient(
            access_key=settings.qiniu.access_key,
            secret_key=settings.qiniu.secret_key,
            bucket=settings.qiniu.bucket,
            domain=settings.qiniu.domain,
        )
    return _qiniu_client
