from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


# 创建数据库引擎。
# pool_pre_ping=True 可以在连接失效时自动检测，适合本地和云服务器部署。
engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# 创建数据库会话工厂。
# 后续每个接口需要访问数据库时，都会从这里获取 Session。
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def check_database_connection() -> bool:
    """执行 SELECT 1，用来检测 MySQL 是否能正常连接。"""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
