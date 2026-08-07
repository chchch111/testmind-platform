import json
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, data: dict | None = None):
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
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    knowledge_base = request_json(
        "POST",
        "/api/rag/knowledge-bases",
        {
            "name": "摄像头硬件测试知识库",
            "description": "用于第五阶段RAG检索测试",
            "product_type": "camera",
            "hardware_module": "night_vision",
            "created_by": 1,
        },
    )
    print("创建知识库：", knowledge_base["knowledge_base_id"])

    source = request_json(
        "POST",
        f"/api/rag/knowledge-bases/{knowledge_base['knowledge_base_id']}/sources/manual",
        {
            "source_name": "摄像头夜视测试规范",
            "source_type": "manual_text",
            "content_text": "摄像头夜视功能测试需要在低照度环境下进行。测试人员应检查红外灯是否自动开启，夜视画面是否清晰，是否存在明显噪点、闪烁、偏色和延迟。异常断电恢复测试需要验证设备重新上电后是否能够恢复视频流输出。长时间录像测试需要关注画面稳定性、存储写入和设备温升。",
            "created_by": 1,
        },
    )
    print("添加知识来源：", source["source_id"])

    build_result = request_json(
        "POST",
        f"/api/rag/knowledge-bases/{knowledge_base['knowledge_base_id']}/build-index?operator_id=1",
    )
    print("FAISS索引构建成功：", build_result["faiss_index_id"])
    print("切片数量：", build_result["chunk_count"])
    print("向量维度：", build_result["vector_dimension"])
    print("索引文件：", build_result["index_file_path"])

    search_result = request_json(
        "POST",
        f"/api/rag/knowledge-bases/{knowledge_base['knowledge_base_id']}/search",
        {
            "query_text": "如何测试摄像头夜视红外灯是否正常开启？",
            "top_k": 3,
        },
    )
    print("检索结果数量：", len(search_result["items"]))
    for item in search_result["items"]:
        print("命中chunk：", item["chunk_id"], "score=", round(item["score"], 4))
        print(item["chunk_text"][:80])

    print("第五阶段RAG知识库闭环测试完成。")


if __name__ == "__main__":
    main()
