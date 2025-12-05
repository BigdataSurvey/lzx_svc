from enum import IntEnum
from typing import Any

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 定义统一业务错误码和 BizException，用于在全局异常处理中返回规范错误响应。
"""

class ErrorCode(IntEnum):
    """
    统一错误码定义，可以根据自己项目慢慢扩展
    """
    SUCCESS = 0

    BUSINESS_ERROR = 10000        # 通用业务异常
    VALIDATION_ERROR = 10001      # 参数校验失败
    NOT_FOUND = 10004             # 资源不存在

    INTERNAL_ERROR = 50000        # 未知系统错误


class BizException(Exception):
    """
    业务异常：在 Service/Router 里显式抛出，用来走统一异常处理
    """
    def __init__(self, code: int, msg: str, data: Any | None = None):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(msg)

    def __str__(self) -> str:
        return f"[{self.code}] {self.msg}"
