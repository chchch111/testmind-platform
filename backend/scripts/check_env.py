from pathlib import Path
import sys

from dotenv import dotenv_values


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
PLACEHOLDER_PASSWORD = "你的MySQL密码"


def mask_secret(value: str) -> str:
    """隐藏敏感信息，只显示是否已填写。"""
    if not value:
        return "未填写"
    return "已填写，不显示具体内容"


def main() -> None:
    """只检查 .env 配置，不连接数据库，不修改任何数据。"""
    if not ENV_FILE.exists():
        print(f"错误：找不到 .env 文件：{ENV_FILE}")
        sys.exit(1)

    config = dotenv_values(ENV_FILE)
    mysql_password = config.get("MYSQL_PASSWORD", "")
    deepseek_api_key = config.get("DEEPSEEK_API_KEY", "")

    print("当前配置文件：", ENV_FILE)
    print("MYSQL_HOST：", config.get("MYSQL_HOST", "未填写"))
    print("MYSQL_PORT：", config.get("MYSQL_PORT", "未填写"))
    print("MYSQL_USER：", config.get("MYSQL_USER", "未填写"))

    if mysql_password == PLACEHOLDER_PASSWORD:
        print("MYSQL_PASSWORD：未修改，仍然是占位文字")
    else:
        print("MYSQL_PASSWORD：", mask_secret(mysql_password))

    print("MYSQL_DATABASE：", config.get("MYSQL_DATABASE", "未填写"))
    print("FAISS_ROOT_DIR：", config.get("FAISS_ROOT_DIR", "未填写"))
    print("UPLOAD_ROOT_DIR：", config.get("UPLOAD_ROOT_DIR", "未填写"))
    print("EXPORT_ROOT_DIR：", config.get("EXPORT_ROOT_DIR", "未填写"))
    print("DEEPSEEK_BASE_URL：", config.get("DEEPSEEK_BASE_URL", "未填写"))
    print("DEEPSEEK_MODEL：", config.get("DEEPSEEK_MODEL", "未填写"))
    print("DEEPSEEK_API_KEY：", mask_secret(deepseek_api_key))


if __name__ == "__main__":
    main()
