from pathlib import Path
import json
import urllib.request
import uuid
import zipfile


BASE_URL = "http://127.0.0.1:8000"
BACKEND_DIR = Path(__file__).resolve().parents[1]
TEMP_DIR = BACKEND_DIR / "tmp"


def request_json(method: str, path: str, data: dict | None = None, timeout: int = 240):
    body = None
    headers = {"Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        url=f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(path: str) -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEMP_DIR / f"full_flow_export_{uuid.uuid4().hex}.xmind"
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=60) as response:
        output_path.write_bytes(response.read())
    return output_path


def ensure_knowledge_base() -> int:
    knowledge_bases = request_json("GET", "/api/rag/knowledge-bases")
    if knowledge_bases:
        return knowledge_bases[0]["knowledge_base_id"]

    knowledge_base = request_json(
        "POST",
        "/api/rag/knowledge-bases",
        {
            "name": "总联调摄像头知识库",
            "description": "用于第七阶段总联调",
            "product_type": "camera",
            "hardware_module": "night_vision",
            "created_by": 1,
        },
    )
    knowledge_base_id = knowledge_base["knowledge_base_id"]

    request_json(
        "POST",
        f"/api/rag/knowledge-bases/{knowledge_base_id}/sources/manual",
        {
            "source_name": "摄像头夜视测试规范",
            "source_type": "manual_text",
            "content_text": "夜视测试需要检查红外灯自动开启、夜视画面清晰度、噪点、闪烁、偏色、延迟，以及异常断电恢复后的重新出流能力。",
            "created_by": 1,
        },
    )
    request_json("POST", f"/api/rag/knowledge-bases/{knowledge_base_id}/build-index?operator_id=1", timeout=600)
    return knowledge_base_id


def main() -> None:
    health = request_json("GET", "/health")
    print("FastAPI健康检查：", health["status"])

    db_health = request_json("GET", "/health/db")
    print("MySQL健康检查：", db_health["status"])

    knowledge_base_id = ensure_knowledge_base()
    print("使用知识库：", knowledge_base_id)

    search_result = request_json(
        "POST",
        f"/api/rag/knowledge-bases/{knowledge_base_id}/search",
        {
            "query_text": "摄像头夜视红外灯和画面清晰度如何测试？",
            "top_k": 3,
        },
        timeout=180,
    )
    print("RAG检索命中数量：", len(search_result["items"]))

    ai_result = request_json(
        "POST",
        "/api/ai/generate-case-set",
        {
            "knowledge_base_id": knowledge_base_id,
            "requirement_text": "生成摄像头夜视功能测试用例，覆盖红外灯、画面清晰度、异常断电恢复。",
            "top_k": 3,
            "created_by": 1,
            "save_to_case_set": True,
        },
        timeout=240,
    )
    print("AI生成记录ID：", ai_result["generation_id"])
    print("AI保存用例集ID：", ai_result["case_set_id"])

    tree = request_json("GET", f"/api/case-sets/{ai_result['case_set_id']}/tree")
    print("生成用例树根节点数量：", len(tree))

    export_path = download_file(f"/api/xmind/export/{ai_result['case_set_id']}?operator_id=1")
    with zipfile.ZipFile(export_path, "r") as xmind_zip:
        names = xmind_zip.namelist()
    print("XMind导出文件：", export_path)
    print("XMind导出包含content.json：", "content.json" in names)

    records = request_json("GET", "/api/ai/generation-records")
    print("AI生成记录总数：", len(records))
    print("第七阶段整体联调完成。")


if __name__ == "__main__":
    main()
