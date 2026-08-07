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

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    case_set = request_json(
        "POST",
        "/api/case-sets",
        {
            "name": "摄像头夜视功能测试用例集",
            "description": "第二阶段API联调用例集",
            "created_by": 1,
        },
    )
    print("创建用例集成功：", case_set["case_set_id"])

    root_node = request_json(
        "POST",
        "/api/case-nodes",
        {
            "case_set_id": case_set["case_set_id"],
            "parent_id": None,
            "node_type": "folder",
            "title": "夜视功能测试",
            "priority": "P1",
            "sort_order": 1,
            "created_by": 1,
        },
    )
    print("创建根节点成功：", root_node["node_id"])

    case_node = request_json(
        "POST",
        "/api/case-nodes",
        {
            "case_set_id": case_set["case_set_id"],
            "parent_id": root_node["node_id"],
            "node_type": "case",
            "title": "红外夜视开启测试",
            "precondition": "设备处于低照度环境，摄像头已正常上电。",
            "test_steps": "1. 进入暗光环境；2. 开启摄像头；3. 观察红外灯是否自动开启。",
            "expected_result": "红外灯自动开启，画面可见且无明显闪烁。",
            "priority": "P0",
            "sort_order": 1,
            "created_by": 1,
        },
    )
    print("创建用例节点成功：", case_node["node_id"])

    updated_node = request_json(
        "PUT",
        f"/api/case-nodes/{case_node['node_id']}",
        {
            "expected_result": "红外灯自动开启，夜视画面清晰，无明显闪烁和噪点。",
            "updated_by": 1,
            "change_note": "补充夜视画面质量要求",
        },
    )
    print("修改用例节点成功：", updated_node["expected_result"])

    versions = request_json("GET", f"/api/case-nodes/{case_node['node_id']}/versions")
    print("历史版本数量：", len(versions))

    first_version_id = versions[-1]["version_id"]
    rollback_node = request_json(
        "POST",
        f"/api/case-nodes/{case_node['node_id']}/rollback/{first_version_id}",
        {
            "operator_id": 1,
            "change_note": "联调测试：回退到初始版本",
        },
    )
    print("回退成功，当前预期结果：", rollback_node["expected_result"])

    tree = request_json("GET", f"/api/case-sets/{case_set['case_set_id']}/tree")
    print("树形结构根节点数量：", len(tree))
    print("API闭环测试完成。")


if __name__ == "__main__":
    main()
