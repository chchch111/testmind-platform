import json
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, data: dict | None = None, expect_error: bool = False):
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

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = json.loads(error.read().decode("utf-8"))
        if expect_error:
            return error.code, error_body
        raise


def main() -> None:
    _, page_data = request_json("GET", "/api/case-sets?page=1&page_size=5")
    print("分页查询成功，总数：", page_data["total"])

    _, case_set = request_json(
        "POST",
        "/api/case-sets",
        {
            "name": "逻辑删除接口测试用例集",
            "description": "用于验证删除接口",
            "created_by": 1,
        },
    )
    print("创建待删除用例集：", case_set["case_set_id"])

    _, root_node = request_json(
        "POST",
        "/api/case-nodes",
        {
            "case_set_id": case_set["case_set_id"],
            "node_type": "folder",
            "title": "删除测试根节点",
            "priority": "P1",
            "created_by": 1,
        },
    )

    _, child_node = request_json(
        "POST",
        "/api/case-nodes",
        {
            "case_set_id": case_set["case_set_id"],
            "parent_id": root_node["node_id"],
            "node_type": "case",
            "title": "删除测试子用例",
            "precondition": "存在根节点",
            "test_steps": "删除根节点",
            "expected_result": "子节点同步逻辑删除",
            "priority": "P2",
            "created_by": 1,
        },
    )
    print("创建父子节点：", root_node["node_id"], child_node["node_id"])

    _, detail = request_json("GET", f"/api/case-nodes/{child_node['node_id']}")
    print("节点详情查询成功：", detail["title"])

    _, delete_node_result = request_json(
        "DELETE",
        f"/api/case-nodes/{root_node['node_id']}",
        {"operator_id": 1},
    )
    print("删除根节点成功，删除节点数量：", delete_node_result["deleted_nodes"])

    status, _ = request_json("GET", f"/api/case-nodes/{child_node['node_id']}", expect_error=True)
    print("删除后查询子节点状态码：", status)

    _, delete_set_result = request_json(
        "DELETE",
        f"/api/case-sets/{case_set['case_set_id']}",
        {"operator_id": 1},
    )
    print("删除用例集成功：", delete_set_result["case_set_id"])

    print("第二阶段补充接口测试完成。")


if __name__ == "__main__":
    main()
