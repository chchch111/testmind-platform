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
            "name": "第四阶段任务测试用例集",
            "description": "用于测试任务创建和执行同步",
            "created_by": 1,
        },
    )
    print("创建用例集：", case_set["case_set_id"])

    root_node = request_json(
        "POST",
        "/api/case-nodes",
        {
            "case_set_id": case_set["case_set_id"],
            "node_type": "folder",
            "title": "摄像头基础功能测试",
            "priority": "P1",
            "created_by": 1,
        },
    )

    case_node = request_json(
        "POST",
        "/api/case-nodes",
        {
            "case_set_id": case_set["case_set_id"],
            "parent_id": root_node["node_id"],
            "node_type": "case",
            "title": "摄像头上电启动测试",
            "precondition": "摄像头连接电源。",
            "test_steps": "1. 接通电源；2. 观察指示灯；3. 检查视频流是否输出。",
            "expected_result": "设备正常启动并输出视频流。",
            "priority": "P0",
            "created_by": 1,
        },
    )
    print("创建执行用例节点：", case_node["node_id"])

    task = request_json(
        "POST",
        "/api/tasks",
        {
            "task_name": "摄像头基础功能回归任务",
            "description": "第四阶段联调任务",
            "case_set_ids": [case_set["case_set_id"]],
            "assignee_ids": [1],
            "created_by": 1,
        },
    )
    print("创建测试任务：", task["task_id"])
    print("执行记录总数：", task["total_executions"])

    executor_tasks = request_json("GET", "/api/executors/1/tasks")
    print("执行人同步任务数量：", len(executor_tasks))

    executions = request_json("GET", f"/api/tasks/{task['task_id']}/executions")
    print("任务执行记录数量：", len(executions))

    first_execution = executions[0]
    updated_execution = request_json(
        "PUT",
        f"/api/executions/{first_execution['execution_id']}",
        {
            "executor_id": 1,
            "execution_status": "passed",
            "actual_result": "设备上电后正常启动，视频流输出正常。",
            "bug_description": None,
            "sync_version": first_execution["sync_version"],
        },
    )
    print("更新执行状态：", updated_execution["execution_status"])
    print("更新后同步版本：", updated_execution["sync_version"])

    detail = request_json("GET", f"/api/tasks/{task['task_id']}")
    print("通过数量：", detail["passed_count"])
    print("未执行数量：", detail["not_run_count"])
    print("任务当前状态：", detail["status"])
    print("第四阶段任务执行同步闭环测试完成。")


if __name__ == "__main__":
    main()
