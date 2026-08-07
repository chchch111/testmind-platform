from pathlib import Path

import bcrypt
import pymysql
from dotenv import dotenv_values


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"



def main() -> None:
    config = dotenv_values(ENV_FILE)
    password_hash = bcrypt.hashpw("admin123456".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    connection = pymysql.connect(
        host=config.get("MYSQL_HOST", "127.0.0.1"),
        port=int(config.get("MYSQL_PORT", 3306)),
        user=config.get("MYSQL_USER", "root"),
        password=config.get("MYSQL_PASSWORD", ""),
        database=config.get("MYSQL_DATABASE", "rag_mindmap_test_platform"),
        charset="utf8mb4",
        autocommit=True,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (user_id, username, password_hash, real_name, role_code, email)
                VALUES (1, 'admin', %s, '系统管理员', 'admin', 'admin@example.com')
                ON DUPLICATE KEY UPDATE
                    password_hash = VALUES(password_hash),
                    real_name = VALUES(real_name),
                    role_code = VALUES(role_code),
                    email = VALUES(email),
                    is_active = 1,
                    is_deleted = 0
                """,
                (password_hash,),
            )
        print("开发管理员用户已准备好：username=admin password=admin123456")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
