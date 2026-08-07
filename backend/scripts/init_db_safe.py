from pathlib import Path
import sys

import pymysql
from dotenv import dotenv_values


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
SQL_FILE = BACKEND_DIR / "sql" / "01_schema.sql"
PLACEHOLDER_PASSWORD = "你的MySQL密码"


def load_env_config() -> dict:
    """读取 .env 里的 MySQL 配置。"""
    if not ENV_FILE.exists():
        print(f"错误：找不到配置文件：{ENV_FILE}")
        sys.exit(1)

    config = dotenv_values(ENV_FILE)
    mysql_password = config.get("MYSQL_PASSWORD", "")

    if mysql_password == PLACEHOLDER_PASSWORD:
        print("错误：请先修改 .env 里的 MYSQL_PASSWORD。")
        sys.exit(1)

    return config


def split_sql_statements(sql_text: str) -> list[str]:
    """把 SQL 文件拆成多条语句。"""
    statements = []
    for statement in sql_text.split(";"):
        clean_statement = statement.strip()
        if clean_statement:
            statements.append(clean_statement)
    return statements


def is_safe_statement(statement: str) -> bool:
    """只允许非破坏性语句，避免误删已有数据。"""
    upper_statement = statement.upper()
    if upper_statement.startswith("DROP "):
        return False
    if upper_statement.startswith("SET FOREIGN_KEY_CHECKS"):
        return False
    return True


def make_create_table_safe(statement: str) -> str:
    """把 CREATE TABLE 转成 CREATE TABLE IF NOT EXISTS。"""
    if statement.upper().startswith("CREATE TABLE "):
        return statement.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
    return statement


def init_database_safely() -> None:
    """安全初始化数据库：只创建不存在的库和表，不删除任何数据。"""
    config = load_env_config()

    if not SQL_FILE.exists():
        print(f"错误：找不到SQL文件：{SQL_FILE}")
        sys.exit(1)

    connection = pymysql.connect(
        host=config.get("MYSQL_HOST", "127.0.0.1"),
        port=int(config.get("MYSQL_PORT", 3306)),
        user=config.get("MYSQL_USER", "root"),
        password=config.get("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
        autocommit=True,
    )

    sql_text = SQL_FILE.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    safe_statements = []

    for statement in statements:
        if not is_safe_statement(statement):
            continue
        safe_statements.append(make_create_table_safe(statement))

    try:
        with connection.cursor() as cursor:
            for index, statement in enumerate(safe_statements, start=1):
                cursor.execute(statement)
                print(f"已执行安全SQL {index}/{len(safe_statements)}")
        print("数据库安全初始化完成。")
    finally:
        connection.close()


if __name__ == "__main__":
    init_database_safely()
