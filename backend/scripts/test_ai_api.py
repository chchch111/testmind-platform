import json
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, data: dict | None = None, timeout: int = 180):
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


def main() -> None:
    knowledge_bases = request_json("GET", "/api/rag/knowledge-bases")
    if not knowledge_bases:
        raise RuntimeError("没有可用知识库，请先运行第五阶段RAG测试")

    knowledge_base_id = knowledge_bases[0]["knowledge_base_id"]
    print("使用知识库：", knowledge_base_id)

    result = request_json(
        "POST",
        "/api/ai/generate-case-set",
        {
            "knowledge_base_id": knowledge_base_id,
            "requirement_text": "请为摄像头夜视功能生成硬件测试用例，重点覆盖红外灯、夜视画面清晰度、异常断电恢复。",
            "top_k": 3,
            "created_by": 1,
            "save_to_case_set": True,
        },
        timeout=180,
    )

    print("AI生成记录ID：", result["generation_id"])
    print("RAG检索记录ID：", result["retrieval_id"])
    print("保存用例集ID：", result["case_set_id"])
    print("生成用例集名称：", result["generated_json"].get("case_set_name"))
    print("顶层节点数量：", len(result["generated_json"].get("nodes", [])))

    tree = request_json("GET", f"/api/case-sets/{result['case_set_id']}/tree")
    print("保存后树根节点数量：", len(tree))

    records = request_json("GET", "/api/ai/generation-records")
    print("AI生成记录数量：", len(records))
    print("第六阶段AI生成测试用例闭环测试完成。")


if __name__ == "__main__":
    main()
