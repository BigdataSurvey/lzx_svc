# encoding: utf-8

from enum import Enum

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/1 下午2:46
@desc: 项目通用常量与枚举定义，集中管理分页、排序等公共配置。
"""

# 通用分页设置
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 1000

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class LangEnum(str, Enum):
    ZH_CN = "zh_CN"
    EN_US = "en_US"