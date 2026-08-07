from pathlib import Path
import json
import urllib.request
import uuid
import zipfile


BASE_URL = "http://127.0.0.1:8000"
BACKEND_DIR = Path(__file__).resolve().parents[1]
TEMP_DIR = BACKEND_DIR / "tmp"


def create_sample_xmind() -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TEMP_DIR / f"sample_{uuid.uuid4().hex}.xmind"

    workbook = [
        {
            "id": "sheet-1",
            "class": "sheet",
            "title": "摄像头硬件测试",
            "rootTopic": {
                "id": "root-topic",
                "title": "摄像头硬件测试",
                "children": {
                    "attached": [
                        {
                            "id": "topic-night",
                            "title": "夜视功能测试",
                            "children": {
                                "attached": [
                                    {
                                        "id": "case-ir",
                                        "title": "红外灯自动开启测试",
                                        "notes": {
                                            "plain": {
                                                "content": "1. 进入暗光环境；2. 启动摄像头；3. 观察红外灯状态。"
                                            }
                                        },
                                    },
                                    {
                                        "id": "case-image",
                                        "title": "夜视画面清晰度测试",
                                        "notes": {
                                            "plain": {
                                                "content": "检查夜视画面是否清晰，无明显噪点和闪烁。"
                                            }
                                        },
                                    },
                                ]
                            },
                        },
                        {
                            "id": "topic-power",
                            "title": "异常断电恢复测试",
                        },
                    ]
                },
            },
        }
    ]

    with zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_DEFLATED) as xmind_zip:
        xmind_zip.writestr("content.json", json.dumps(workbook, ensure_ascii=False, indent=2))
        xmind_zip.writestr("metadata.json", json.dumps({"creator": "test_script"}, ensure_ascii=False))
        xmind_zip.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}}}, ensure_ascii=False))

    return file_path


def post_multipart_xmind(file_path: Path) -> dict:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    file_bytes = file_path.read_bytes()

    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode("utf-8"),
            b"Content-Type: application/vnd.xmind.workbook\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )

    request = urllib.request.Request(
        url=f"{BASE_URL}/api/xmind/import?created_by=1",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download_export(case_set_id: int) -> Path:
    export_path = TEMP_DIR / f"export_{case_set_id}_{uuid.uuid4().hex}.xmind"
    with urllib.request.urlopen(f"{BASE_URL}/api/xmind/export/{case_set_id}?operator_id=1", timeout=30) as response:
        export_path.write_bytes(response.read())
    return export_path


def main() -> None:
    sample_path = create_sample_xmind()
    print("样例XMind已生成：", sample_path)

    import_result = post_multipart_xmind(sample_path)
    print("导入成功，用例集ID：", import_result["case_set_id"])
    print("导入节点数量：", import_result["node_count"])

    tree = get_json(f"/api/case-sets/{import_result['case_set_id']}/tree")
    print("导入后树根节点数量：", len(tree))

    export_path = download_export(import_result["case_set_id"])
    print("导出成功：", export_path)

    with zipfile.ZipFile(export_path, "r") as xmind_zip:
        names = xmind_zip.namelist()
        print("导出文件内容：", names)
        assert "content.json" in names

    print("XMind导入导出闭环测试完成。")


if __name__ == "__main__":
    main()
