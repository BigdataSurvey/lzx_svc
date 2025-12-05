# encoding: utf-8
from __future__ import annotations

import os
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvEnum(str, Enum):
    local = "local"
    dev = "dev"
    test = "test"
    prod = "prod"


class LoggingSettings(BaseModel):
    level: str = "INFO"
    show_sql: bool = False


class HttpSettings(BaseModel):
    timeout: int = 10
    max_retries: int = 3
    proxy: Optional[str] = None


class MysqlSettings(BaseModel):
    """
    MySQL 相关配置：
    - main_url: 主库连接串
    - back_url: 备库 1（比如蘑菇钉推荐）
    - back2_url: 备库 2（比如大数据）
    """
    main_url: str = ""
    back_url: Optional[str] = None
    back2_url: Optional[str] = None


class DorisSettings(BaseModel):
    """
    Doris 相关配置：
    - url: 查询库连接串（9030）
    - streaming_url: 如有流式写入 / FE 其他端口可扩展
    """
    url: str = ""
    streaming_url: Optional[str] = None


class RedisSettings(BaseModel):
    url: str = ""


class MongoSettings(BaseModel):
    primary_uri: str = ""
    attendence_uri: Optional[str] = None


class EsSettings(BaseModel):
    hosts: List[str] = []


class QiniuSettings(BaseModel):
    access_key: str = ""
    secret_key: str = ""
    bucket: str = ""
    domain: str = ""


class KafkaSettings(BaseModel):
    bootstrap_servers: str = ""
    username: Optional[str] = None
    password: Optional[str] = None


class LlmSettings(BaseModel):
    """
    大模型相关配置，预留多家厂商：
    - provider: 当前默认使用的厂商（openai / dashscope / volc 等）
    - endpoint / openai_base_url 等都是可选
    """
    provider: str = "none"
    endpoint: Optional[AnyUrl] = None

    openai_base_url: Optional[AnyUrl] = None
    openai_api_key: Optional[str] = None

    dashscope_api_key: Optional[str] = None
    dashscope_vision_api_key: Optional[str] = None
    dashscope_backup_api_key: Optional[str] = None

    volc_api_key: Optional[str] = None
    volc_base_url: Optional[AnyUrl] = None
    volc_model: Optional[str] = None

    default_user: Optional[str] = None


class SshTunnelSettings(BaseModel):
    """
    全局 SSH 跳板机配置（统一控制 MySQL / Doris 等是否走 SSH）：
    - enabled: 是否启用 SSH 隧道
    - ssh_host / ssh_port: 跳板机地址
    - ssh_username / ssh_password: SSH 登录凭据
    - private_key_path: 如需走私钥，可在 .env.* 中配置
    """
    enabled: bool = False
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_username: str = ""
    ssh_password: str = ""
    private_key_path: Optional[str] = None


class Settings(BaseSettings):
    """
    全局配置入口。

    通过 pydantic-settings 从以下文件加载配置：
    - .env
    - .env.<env>  （env 由 OS 环境变量 APP_ENV 决定，默认 prod）

    嵌套配置使用 env_nested_delimiter="__"：
    - MYSQL__MAIN_URL       -> settings.mysql.main_url
    - MYSQL__BACK_URL       -> settings.mysql.back_url
    - MYSQL__BACK2_URL      -> settings.mysql.back2_url
    - DORIS__URL            -> settings.doris.url
    - REDIS__URL            -> settings.redis.url
    - SSH_TUNNEL__ENABLED   -> settings.ssh_tunnel.enabled
    等等。
    """
    model_config = SettingsConfigDict(
        extra="ignore",
        env_nested_delimiter="__",
    )

    app_name: str = "lzx_svc"
    debug: bool = True
    api_prefix: str = "/api"

    # 只是标记当前环境，用于日志展示，真正选择 .env.<env> 的是 OS 的 APP_ENV
    env: EnvEnum = EnvEnum.local

    logging: LoggingSettings = LoggingSettings()
    http: HttpSettings = HttpSettings()

    mysql: MysqlSettings = MysqlSettings()
    doris: DorisSettings = DorisSettings()
    redis: RedisSettings = RedisSettings()
    mongo: MongoSettings = MongoSettings()
    es: EsSettings = EsSettings()
    qiniu: QiniuSettings = QiniuSettings()
    kafka: KafkaSettings = KafkaSettings()
    llm: LlmSettings = LlmSettings()

    ssh_tunnel: SshTunnelSettings = SshTunnelSettings()


def get_settings() -> "Settings":
    """
    读取 OS 环境变量 APP_ENV 来决定加载哪一个 .env.<env> 文件。
    如果 APP_ENV 非法，则回退为 local。
    """
    env_from_os = os.getenv("APP_ENV", "prod")
    try:
        env = EnvEnum(env_from_os)
    except ValueError:
        env = EnvEnum.local

    base_env_file = ".env"
    env_specific_file = f".env.{env.value}"

    return Settings(
        _env_file=[base_env_file, env_specific_file],
        _env_file_encoding="utf-8",
    )


settings: Settings = get_settings()


def dump_critical_config() -> None:
    """
    调试用：打印与环境 / Doris / SSH 隧道相关的关键配置。

    建议：
    - 在独立脚本（如 doris_ssh_test.py）开头调用一次；
    - 在 FastAPI 应用启动时调用一次；

    对比两边输出，可以精确确认：
    - APP_ENV
    - settings.env
    - settings.doris.url
    - settings.ssh_tunnel.*
    是否一致。
    """
    print("=== CONFIG DEBUG ===")
    print(f"os.getenv('APP_ENV')       = {os.getenv('APP_ENV')!r}")
    print(f"settings.env              = {settings.env.value!r}")
    print(f"settings.doris.url        = {settings.doris.url!r}")
    ssh = settings.ssh_tunnel
    print(
        "settings.ssh_tunnel = {"
        f"enabled={ssh.enabled!r}, "
        f"ssh_host={ssh.ssh_host!r}, "
        f"ssh_port={ssh.ssh_port!r}, "
        f"ssh_username={ssh.ssh_username!r}"
        "}"
    )
    print("====================")
