# encoding: utf-8

from fastapi.testclient import TestClient

from main import app

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午4:20
@desc: 健康检查接口的基础自动化测试。
"""

client = TestClient(app)


def test_health_ok():
    """
    检查 /api/health 接口是否可以正常访问，并返回约定结构。
    """
    resp = client.get("/api/health")
    assert resp.status_code == 200

    data = resp.json()
    # 这里只做最小约束，避免和内部实现强耦合
    assert isinstance(data, dict)
    assert data.get("code") == 0
    assert data.get("msg") == "ok"
    assert isinstance(data.get("data"), dict)
    # data 里一般会有 status 字段（如果你后续改掉，这里也可以跟着调整）
    assert data["data"].get("status") in ("ok", "healthy")
