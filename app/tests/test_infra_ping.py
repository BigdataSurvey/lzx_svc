# encoding: utf-8

from fastapi.testclient import TestClient

from main import app

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午4:20
@desc: 基础设施探活接口的自动化测试（以 MySQL 为例）。
"""

client = TestClient(app)


def test_infra_ping_mysql():
    """
    检查 /api/infra/ping/mysql 是否返回 code=0。
    前提：你的 .env.local 中 MySQL 配置可用。
    """
    resp = client.get("/api/infra/ping/mysql")
    assert resp.status_code == 200

    body = resp.json()
    assert body.get("code") == 0
    assert body.get("msg") == "ok"
    assert isinstance(body.get("data"), dict)
    # data 里通常会返回 ok / version 等字段，这里只简单判断一下
    assert body["data"].get("ok") is True
