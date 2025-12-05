# encoding: utf-8
from __future__ import annotations

import warnings
import sys

# ============================================================
# [终极屏蔽] 在导入任何第三方库之前，先设置这一层过滤
# 1. 忽略 cryptography 模块发出的所有警告
warnings.filterwarnings("ignore", module="cryptography")
# 2. 忽略 paramiko 模块发出的所有警告
warnings.filterwarnings("ignore", module="paramiko")
# 3. 忽略任何包含 "TripleDES" 字样的警告（正则匹配）
warnings.filterwarnings("ignore", message=".*TripleDES.*")
# ============================================================

import pymysql
from sqlalchemy.engine.url import make_url
from app.core.config import settings, dump_critical_config

def test_doris_via_ssh() -> None:
    """
    独立脚本：通过 SSH 隧道测试 Doris 连接是否正常。
    """
    # 先打印关键配置
    dump_critical_config()

    url = make_url(settings.doris.url)
    remote_host = url.host
    remote_port = url.port or 9030
    db_user = url.username
    db_password = url.password
    db_name = url.database

    ssh_cfg = settings.ssh_tunnel

    print("=== Doris SSH 连接 ===")
    print(f"当前 settings.env          = {settings.env.value}")
    print(f"SSH 跳板机: {ssh_cfg.ssh_username}@{ssh_cfg.ssh_host}:{ssh_cfg.ssh_port}")
    print(f"Doris 数据库: {db_user}@{remote_host}:{remote_port}/{db_name}")

    if not ssh_cfg.enabled:
        print("当前 ssh_tunnel.enabled = False，prod 配置需要改为 true 才会走 SSH。")
        return

    # 这里再次加锁，确保万无一失
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from sshtunnel import SSHTunnelForwarder

    with SSHTunnelForwarder(
        (ssh_cfg.ssh_host, ssh_cfg.ssh_port),
        ssh_username=ssh_cfg.ssh_username,
        ssh_password=ssh_cfg.ssh_password,
        remote_bind_address=(remote_host, remote_port),
        # 本地随机端口
        local_bind_address=("127.0.0.1", 0),
    ) as tunnel:
        local_port = tunnel.local_bind_port
        print(f"SSH Tunnel 已建立: 127.0.0.1:{local_port} -> {remote_host}:{remote_port}")

        conn = pymysql.connect(
            host="127.0.0.1",
            port=local_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset="utf8mb4",
            autocommit=True,
        )

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                print("查询结果：", row)
        finally:
            conn.close()
            print("Doris 连接已关闭")
            print("=== Doris SSH 关闭 ===")


if __name__ == "__main__":
    test_doris_via_ssh()