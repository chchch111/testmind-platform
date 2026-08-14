"""纯单元测试：只测不依赖数据库/外部网络的服务层纯函数。

运行方式（在 backend 目录下）：
    .venv/Scripts/python.exe -m pytest tests -v
"""
import pytest

from app.services.ai_service import MAX_GENERATED_NODE_COUNT, build_user_prompt, parse_generated_json
from app.services.task_service import VALID_EXECUTION_STATUS
from app.services.xmind_service import build_tagged_title, safe_xmind_error_message


class TestParseGeneratedJson:
    def test_plain_json(self):
        text = '{"case_set_name": "夜视测试", "nodes": [{"title": "红外灯测试"}]}'
        result = parse_generated_json(text)
        assert result["case_set_name"] == "夜视测试"
        assert result["nodes"][0]["title"] == "红外灯测试"

    def test_json_with_markdown_fence(self):
        text = '```json\n{"case_set_name": "a", "nodes": [{"title": "x"}]}\n```'
        result = parse_generated_json(text)
        assert result["case_set_name"] == "a"

    def test_json_with_surrounding_noise(self):
        text = '好的，结果如下：\n{"case_set_name": "b", "nodes": [{"title": "x"}]}\n希望对你有帮助'
        result = parse_generated_json(text)
        assert result["nodes"][0]["title"] == "x"

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            parse_generated_json('{"nodes": []}')

    def test_nodes_not_list(self):
        with pytest.raises(ValueError):
            parse_generated_json('{"case_set_name": "a", "nodes": "x"}')

    def test_empty_nodes_rejected(self):
        with pytest.raises(ValueError):
            parse_generated_json('{"case_set_name": "a", "nodes": []}')

    def test_not_json_at_all(self):
        with pytest.raises(ValueError):
            parse_generated_json("这不是JSON")

    def test_normalizes_invalid_priority_and_missing_case_fields(self):
        text = """
        {
          "case_set_name": "质量校验",
          "nodes": [
            {"title": "空字段用例", "node_type": "case", "priority": "P9", "children": []}
          ]
        }
        """
        result = parse_generated_json(text)
        node = result["nodes"][0]
        assert node["priority"] == "P1"
        assert node["test_steps"] == "待人工补充测试步骤"
        assert node["expected_result"] == "待人工补充预期结果"
        assert result["quality_warnings"]

    def test_rejects_too_deep_tree(self):
        text = '{"case_set_name":"a","nodes":[{"title":"1","children":[{"title":"2","children":[{"title":"3","children":[{"title":"4","children":[{"title":"5","children":[{"title":"6","children":[{"title":"7"}]}]}]}]}]}]}]}'
        with pytest.raises(ValueError, match="层级过深"):
            parse_generated_json(text)

    def test_rejects_too_many_nodes(self):
        nodes = ",".join('{"title":"n%s"}' % index for index in range(MAX_GENERATED_NODE_COUNT + 1))
        with pytest.raises(ValueError, match="节点过多"):
            parse_generated_json(f'{{"case_set_name":"a","nodes":[{nodes}]}}')


class TestBuildTaggedTitle:
    def test_no_tags(self):
        assert build_tagged_title("红外灯测试", []) == "红外灯测试"

    def test_single_tag(self):
        assert build_tagged_title("红外灯测试", ["主流程"]) == "【主流程】红外灯测试"

    def test_multiple_tags_deduplicated(self):
        assert build_tagged_title("测试", ["主流程", "主流程", "安全"]) == "【主流程】【安全】测试"

    def test_blank_tags_ignored(self):
        assert build_tagged_title("测试", ["  ", "", "性能"]) == "【性能】测试"


class TestSafeXmindError:
    def test_http_exception_passthrough(self):
        from fastapi import HTTPException

        exc = HTTPException(status_code=400, detail="当前仅支持包含content.json的新版XMind文件")
        assert safe_xmind_error_message(exc) == "当前仅支持包含content.json的新版XMind文件"

    def test_known_messages_preserved(self):
        assert safe_xmind_error_message(ValueError("上传文件不是有效的XMind压缩包")) == "上传文件不是有效的XMind压缩包"
        assert safe_xmind_error_message(ValueError("XMind层级过深，导入终止")) == "XMind层级过深，导入终止"

    def test_unknown_error_sanitized(self):
        message = safe_xmind_error_message(ValueError("PermissionError: [Errno 13] D:\\secret\\path\\file.xmind"))
        assert "D:" not in message
        assert message.startswith("XMind导入失败")


class TestExecutionStatus:
    def test_valid_statuses_include_skipped(self):
        assert "skipped" in VALID_EXECUTION_STATUS
        assert VALID_EXECUTION_STATUS == {"not_run", "passed", "failed", "blocked", "skipped"}


class TestBuildUserPrompt:
    def test_contains_requirement_and_context(self):
        prompt = build_user_prompt("测试夜视红外灯", [{"chunk_text": "红外灯应在低照度自动开启。"}])
        assert "测试夜视红外灯" in prompt
        assert "红外灯应在低照度自动开启。" in prompt
        assert "case_set_name" in prompt
