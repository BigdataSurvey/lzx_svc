# encoding: utf-8
from __future__ import annotations

import asyncio
import warnings
import asyncmy
from sqlalchemy.engine.url import make_url
from sshtunnel import SSHTunnelForwarder

# 引入项目配置
from app.core.config import settings, dump_critical_config

# ============================================================
# [Fix] 屏蔽 Paramiko < 3.0 产生的 TripleDES 警告
# ============================================================
warnings.filterwarnings("ignore", module="cryptography")
warnings.filterwarnings("ignore", module="paramiko")
warnings.filterwarnings("ignore", message=".*TripleDES.*")

"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/5 下午5:33
@desc: MYSQL SSH 测试
"""

async def test_mysql_via_ssh_async() -> None:
    """
    独立脚本：通过 SSH 隧道测试 MySQL (asyncmy) 连接是否正常。

    注意：MySQL 在本项目中使用的是异步驱动 (asyncmy)，
    所以这个测试脚本必须也是异步的。
    """
    dump_critical_config()

    # 1. 解析配置中的 MySQL URL
    url_obj = make_url(settings.mysql.main_url)
    remote_host = url_obj.host
    remote_port = url_obj.port or 3306
    db_user = url_obj.username
    db_password = url_obj.password
    db_name = url_obj.database

    ssh_cfg = settings.ssh_tunnel

    print("\n=== MySQL (Async) SSH 连接测试 ===")
    print(f"当前 APP_ENV               = {settings.env.value}")
    print(f"SSH 跳板机                 = {ssh_cfg.ssh_username}@{ssh_cfg.ssh_host}:{ssh_cfg.ssh_port}")
    print(f"MySQL 目标库               = {db_user}@{remote_host}:{remote_port}/{db_name}")

    # 2. 如果未开启 SSH，直接退出或尝试直连
    if not ssh_cfg.enabled:
        print(">>> 警告: SSH_TUNNEL__ENABLED = False，将尝试直接连接目标库...")
        local_host = remote_host
        local_port = remote_port
        tunnel = None
    else:
        # 3. 建立 SSH 隧道
        print(">>> 正在建立 SSH 隧道...")
        tunnel = SSHTunnelForwarder(
            (ssh_cfg.ssh_host, ssh_cfg.ssh_port),
            ssh_username=ssh_cfg.ssh_username,
            ssh_password=ssh_cfg.ssh_password,
            remote_bind_address=(remote_host, remote_port),
            # 本地随机端口 (0)
            local_bind_address=("127.0.0.1", 0),
        )
        tunnel.start()
        local_host = "127.0.0.1"
        local_port = tunnel.local_bind_port
        print(f">>> SSH Tunnel 已建立: {local_host}:{local_port} -> {remote_host}:{remote_port}")

    try:
        # 4. 使用 asyncmy 进行连接测试
        # 注意：这里模拟的是 SQLAlchemy 底层 create_async_engine 的行为
        print(f">>> 正在通过 asyncmy 连接到 {local_host}:{local_port} ...")

        conn = await asyncmy.connect(
            host=local_host,
            port=local_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset="utf8mb4",
            autocommit=True,
        )

        print(">>> MySQL 连接成功！")

        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            result = await cur.fetchone()
            print(f">>> SQL 执行结果 (SELECT 1): {result}")

            # 可选：再查一下版本，确认连的是对的库
            await cur.execute("SELECT @@version")
            version = await cur.fetchone()
            print(f">>> 数据库版本: {version}")

        conn.close()
        print(">>> MySQL 连接已关闭")

    except Exception as e:
        print(f"\n!!! 连接或查询失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 5. 关闭隧道
        if tunnel:
            tunnel.stop()
            print("=== SSH Tunnel 已关闭 ===")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(test_mysql_via_ssh_async())