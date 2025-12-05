# app/infra/ssh_tunnel.py（核心代码）

from typing import Dict, Tuple, Optional

from loguru import logger
from sshtunnel import SSHTunnelForwarder
from sqlalchemy.engine.url import make_url, URL

from app.core.config import settings

_TUNNELS: Dict[Tuple[str, int], SSHTunnelForwarder] = {}


def _ssh_enabled() -> bool:
    cfg = settings.ssh_tunnel
    if not cfg.enabled:
        return False
    if not (cfg.ssh_host and cfg.ssh_username):
        logger.warning("[ssh_tunnel] ssh_tunnel.enabled=True 但 host/username 未配置完整")
        return False
    return True


def get_tunneled_url(original_url: str) -> str:
    """
    将原始 DB URL（可能是远程 IP/端口）转换为走 SSH 隧道的 URL。

    - 如果 SSH 未启用，直接返回 original_url；
    - 如果启用：
      1）解析 original_url 拿到 host/port；
      2）为 (host, port) 建立 / 复用 SSH 隧道；
      3）返回一个新的 URL：host=127.0.0.1, port=local_bind_port，
         其他（user/password/db/query）保持不变。
    """
    logger.info(f"[ssh_tunnel] input url={original_url!r}, enabled={_ssh_enabled()}")

    if not original_url:
        return original_url

    if not _ssh_enabled():
        logger.info("[ssh_tunnel] ssh not enabled, return original url")
        return original_url

    url = make_url(original_url)
    remote_host: Optional[str] = url.host
    remote_port: Optional[int] = url.port

    if not remote_host or not remote_port:
        logger.warning("[ssh_tunnel] url 缺少 host/port，直接返回 original_url")
        return original_url

    key = (remote_host, remote_port)
    forwarder = _TUNNELS.get(key)

    if forwarder is None or not forwarder.is_active:
        cfg = settings.ssh_tunnel
        logger.info(
            f"[ssh_tunnel] creating SSH tunnel: ssh={cfg.ssh_username}@{cfg.ssh_host}:{cfg.ssh_port} "
            f"remote_bind={remote_host}:{remote_port}"
        )
        forwarder = SSHTunnelForwarder(
            (cfg.ssh_host, cfg.ssh_port),
            ssh_username=cfg.ssh_username,
            ssh_password=cfg.ssh_password,
            remote_bind_address=key,
            local_bind_address=("127.0.0.1", 0),
        )
        forwarder.start()
        _TUNNELS[key] = forwarder

        logger.info(
            f"[ssh_tunnel] SSH tunnel created: 127.0.0.1:{forwarder.local_bind_port} -> "
            f"{remote_host}:{remote_port}"
        )

    # 构造新的 URL（host 替换为 127.0.0.1，port 替换为本地端口）
    new_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host="127.0.0.1",
        port=forwarder.local_bind_port,
        database=url.database,
        query=url.query,
    )

    # 【核心修正】
    # !!! 千万不能用 str(new_url) 给 driver 用 !!!
    # str(new_url) 在 SQLAlchemy 2.x 中会把密码替换为 ***
    full_url = new_url.render_as_string(hide_password=False)

    # 日志里用脱敏版本
    logger.info(f"[ssh_tunnel] output url={str(new_url)!r}")

    return full_url


def close_all_tunnels() -> None:
    """在应用关闭时调用，统一关闭所有隧道。"""
    for key, fwd in list(_TUNNELS.items()):
        try:
            logger.info(
                f"[ssh_tunnel] stopping SSH tunnel for {key[0]}:{key[1]} ..."
            )
            fwd.stop()
        except Exception as e:
            logger.warning(f"[ssh_tunnel] error stopping SSH tunnel {key}: {e}")
    _TUNNELS.clear()
