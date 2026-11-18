"""项目配置：从 .env 读取，未配置时使用下方默认值（仅用于本地演示）。"""
import logging

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# 通义 DashScope 的正确域名：dashscope.aliyuncs.com（aliyun + cs）
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # 基本信息
    app_name: str = "云东AI购"
    api_prefix: str = "/api/v1"

    # MySQL（生产用 MySQL 8；本地演示可把 URL 改成 sqlite 跑通骨架）
    mysql_user: str = "root"
    mysql_password: str = "root"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_db: str = "yd_ai_shop"
    # 直接给连接串，留空则用上面的 MySQL 配置拼
    db_url: str = ""

    # 鉴权
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # 大模型网关（兼容 OpenAI 协议；默认用通义 DashScope）
    llm_api_key: str = ""
    llm_base_url: str = DASHSCOPE_BASE_URL
    llm_model: str = "qwen-plus"
    embed_model: str = "text-embedding-v3"

    # 向量库（Day2 用）
    milvus_uri: str = "./milvus.db"

    # 前端静态目录（相对 backend 目录）
    frontend_dir: str = "../frontend"

    @field_validator("llm_base_url")
    @classmethod
    def _normalize_base_url(cls, v: str) -> str:
        """兜住手写 .env 的四种常见错误，改完仍是标准 base_url：
        1. 没写协议头；2. 域名少 cs；3. 末尾多斜杠；4. 误把接口路径写进来。
        """
        raw = (v or "").strip().strip('"').strip("'")
        if not raw:
            return DASHSCOPE_BASE_URL

        val = raw
        if not val.lower().startswith(("http://", "https://")):
            logger.warning("LLM_BASE_URL没写协议头(%s)，已按https://补全", raw)
            val = "https://" + val.lstrip("/")

        if "dashscope.aliyun.com" in val:
            logger.warning("LLM_BASE_URL域名少一个cs，已自动改为 dashscope.aliyuncs.com")
            val = val.replace("dashscope.aliyun.com", "dashscope.aliyuncs.com")

        val = val.rstrip("/")
        for suffix in ("/embeddings", "/chat/completions", "/completions"):
            if val.endswith(suffix):
                logger.warning("LLM_BASE_URL不该带接口路径%s，已去掉", suffix)
                val = val[: -len(suffix)].rstrip("/")
        return val


# 单例，必须放在 Settings 模块最后
settings = Settings()
