from typing import Any, Optional
from pydantic import BaseModel

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: 定义统一 API 返回结构及成功/失败辅助方法，规范接口响应格式。
"""
class ApiResponse(BaseModel):
    """
    所有接口统一返回结构：
    {
      "code": 0,
      "msg": "ok",
      "data": ...
    }
    """
    code: int = 0
    msg: str = "ok"
    data: Optional[Any] = None


def success(data: Any | None = None, msg: str = "ok") -> ApiResponse:
    """
    业务成功时调用：
        return success({...})
    """
    return ApiResponse(code=0, msg=msg, data=data)


def fail(code: int = -1, msg: str = "error", data: Any | None = None) -> ApiResponse:
    """
    业务失败/异常时统一用这个结构：
        return fail(1001, "xxx 不存在")
    通常在异常处理器里用得更多。
    """
    return ApiResponse(code=code, msg=msg, data=data)
