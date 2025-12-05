# encoding: utf-8
"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/12/3 下午3:20
@desc: 全局配置管理模块，基于 Pydantic BaseSettings 实现。
       负责加载环境变量与 .env 文件，定义并校验项目所需的各项配置。
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Optional, List

from dotenv import load_dotenv
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
    """MySQL 相关配置"""
    main_url: str = ""
    back_url: Optional[str] = None
    back2_url: Optional[str] = None


class DorisSettings(BaseModel):
    """Doris 相关配置"""
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
    """大模型相关配置"""
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
    """全局 SSH 跳板机配置"""
    enabled: bool = False
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_username: str = ""
    ssh_password: str = ""
    private_key_path: Optional[str] = None


class Settings(BaseSettings):
    """全局配置入口"""
    model_config = SettingsConfigDict(
        extra="ignore",
        env_nested_delimiter="__",
        env_file_encoding="utf-8"
    )

    app_name: str = "lzx_svc"
    debug: bool = True
    api_prefix: str = "/api"

    # 跨域允许列表，生产环境应配置具体域名
    # 在 .env 中配置示例: BACKEND_CORS_ORIGINS=["http://localhost:3000", "https://my.site.com"]
    backend_cors_origins: List[str] = ["*"]

    # 环境标记
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
    """加载配置逻辑"""
    load_dotenv(".env")
    env_from_os = os.getenv("APP_ENV", "local")

    try:
        env = EnvEnum(env_from_os)
    except ValueError:
        env = EnvEnum.local

    base_env_file = ".env"
    env_specific_file = f".env.{env.value}"

    return Settings(
        _env_file=[base_env_file, env_specific_file]
    )


settings: Settings = get_settings()


def dump_critical_config() -> None:
    """调试用：打印关键配置"""
    print("=== CONFIG DEBUG ===")
    print(f"os.getenv('APP_ENV')       = {os.getenv('APP_ENV')!r}")
    print(f"settings.env              = {settings.env.value!r}")
    print(f"settings.doris.url        = {settings.doris.url!r}")
    print(f"settings.backend_cors_origins = {settings.backend_cors_origins!r}")
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