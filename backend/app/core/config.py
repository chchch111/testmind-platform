from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
PROJECT_ROOT = BACKEND_DIR.parent


def _resolve_storage_path(value: str, default_relative: str) -> str:
    """存储路径优先读 .env；若为空则相对项目根目录生成绝对路径。"""
    path_text = (value or "").strip()
    if path_text:
        return path_text
    return str(PROJECT_ROOT / default_relative)


class Settings(BaseSettings):
    """统一读取 .env 配置，避免把密码、API Key 写死在代码里。"""

    app_name: str = "TestMind"
    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "rag_mindmap_test_platform"

    faiss_root_dir: str = ""
    upload_root_dir: str = ""
    export_root_dir: str = ""

    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    hf_home: str = ""
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 80
    rag_top_k: int = 5

    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_api_key: str = ""

    auth_secret_key: str = "rag-mindmap-dev-secret-change-me"
    auth_token_expire_minutes: int = 60 * 24

    max_upload_mb: int = 20

    cors_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def mysql_url(self) -> str:
        """生成 SQLAlchemy 使用的 MySQL 连接地址。"""
        safe_user = quote_plus(self.mysql_user)
        safe_password = quote_plus(self.mysql_password)
        safe_database = quote_plus(self.mysql_database)
        return (
            f"mysql+pymysql://{safe_user}:{safe_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{safe_database}"
            "?charset=utf8mb4"
        )

    @property
    def faiss_root(self) -> str:
        return _resolve_storage_path(self.faiss_root_dir, "storage/faiss")

    @property
    def upload_root(self) -> str:
        return _resolve_storage_path(self.upload_root_dir, "storage/uploads")

    @property
    def export_root(self) -> str:
        return _resolve_storage_path(self.export_root_dir, "storage/exports")

    @property
    def hf_home_dir(self) -> str:
        return _resolve_storage_path(self.hf_home, "storage/models/huggingface")

    @property
    def cors_origins_list(self) -> list[str]:
        """逗号分隔的允许跨域来源，空则默认放行前端开发地址。"""
        if self.cors_origins.strip():
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return ["http://127.0.0.1:5173", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求都重复读取 .env 文件。"""
    return Settings()


settings = get_settings()
