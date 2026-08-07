from pathlib import Path
import json
import sys
import urllib.error
import urllib.request

from dotenv import dotenv_values


# 当前文件在 backend/scripts 下，所以 parents[1] 就是 backend 目录。
BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


def load_deepseek_config() -> dict:
    """从 .env 读取 DeepSeek 配置，避免在代码里硬编码密钥。"""
    if not ENV_FILE.exists():
        print("ERROR: .env file not found")
        sys.exit(1)

    config = dotenv_values(ENV_FILE)
    api_key = config.get("DEEPSEEK_API_KEY", "")

    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY is empty")
        sys.exit(1)

    return config


def call_deepseek() -> None:
    """发送一次最小测试请求，验证 DeepSeek-v4-flash 是否可以正常调用。"""
    config = load_deepseek_config()

    base_url = config.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = config.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    api_key = config.get("DEEPSEEK_API_KEY", "")

    url = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "禁止输出思考过程，禁止输出推理草稿，禁止输出<reasoning>标签内容，只输出最终答案。",
            },
            {
                "role": "user",
                "content": "请只返回一句话：DeepSeek API 连接测试成功。",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 100,
    }

    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_text = response.read().decode("utf-8")
            response_json = json.loads(response_text)
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        print("ERROR: HTTP request failed")
        print("STATUS:", error.code)
        print("BODY:", error_body)
        sys.exit(1)
    except Exception as error:
        print("ERROR: request failed")
        print(type(error).__name__, str(error))
        sys.exit(1)

    content = response_json["choices"][0]["message"]["content"]

    print("STATUS: OK")
    print("MODEL:", model)
    print("RESPONSE:", content)


if __name__ == "__main__":
    call_deepseek()
