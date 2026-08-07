from pathlib import Path
import sys

import pymysql
from dotenv import dotenv_values


# backend目录：当前文件是 backend/scripts/init_db.py，所以 parents[1] 就是 backend。
BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
SQL_FILE = BACKEND_DIR / "sql" / "01_schema.sql"


PLACEHOLDER_PASSWORD = "你的MySQL密码"


def load_env_config() -> dict:
    """读取 .env 文件里的 MySQL 配置。"""
    if not ENV_FILE.exists():
        print(f"错误：找不到配置文件：{ENV_FILE}")
        print("请先把 .env.example 复制为 .env，并填写 MySQL 密码。")
        sys.exit(1)

    config = dotenv_values(ENV_FILE)
    mysql_password = config.get("MYSQL_PASSWORD", "")

    if mysql_password == PLACEHOLDER_PASSWORD:
        print("错误：你还没有修改 .env 里的 MYSQL_PASSWORD。")
        print(f"请打开文件：{ENV_FILE}")
        print("把 MYSQL_PASSWORD=你的MySQL密码 改成你本机真实的 MySQL 密码。")
        sys.exit(1)

    return config


def split_sql_statements(sql_text: str) -> list[str]:
    """把建表SQL按分号拆成多条语句。"""
    statements = []
    for statement in sql_text.split(";"):
        clean_statement = statement.strip()
        if clean_statement:
            statements.append(clean_statement)
    return statements


def init_database() -> None:
    """连接 MySQL 并执行 01_schema.sql。"""
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

    try:
        with connection.cursor() as cursor:
            for index, statement in enumerate(statements, start=1):
                cursor.execute(statement)
                print(f"已执行第 {index}/{len(statements)} 条SQL")
        print("数据库初始化完成。")
    finally:
        connection.close()


if __name__ == "__main__":
    init_database()
