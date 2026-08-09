from pathlib import Path
import json
import shutil
import uuid
import zipfile

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.case import TestCaseNode, TestCaseSet
from app.models.xmind import XMindFile, XMindImportBatch
from app.services.case_service import create_node_version, ensure_user_exists, node_to_dict


MAX_IMPORT_DEPTH = 20


def import_xmind_file(db: Session, file: UploadFile, created_by: int) -> dict:
    ensure_user_exists(db, created_by)

    if not file.filename or not file.filename.lower().endswith(".xmind"):
        raise HTTPException(status_code=400, detail="只支持上传.xmind文件")

    upload_dir = Path(settings.upload_root) / "xmind"
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_name = f"{uuid.uuid4()}_{file.filename}"
    saved_path = upload_dir / saved_name

    with saved_path.open("wb") as target_file:
        shutil.copyfileobj(file.file, target_file)

    xmind_file = XMindFile(
        file_name=file.filename,
        file_path=str(saved_path),
        file_type="import",
        file_size=saved_path.stat().st_size,
        process_status="pending",
        created_by=created_by,
    )
    db.add(xmind_file)
    db.flush()

    try:
        root_topic = read_xmind_root_topic(saved_path)
        case_set = TestCaseSet(
            name=root_topic.get("title") or saved_path.stem,
            description=f"由XMind文件导入：{file.filename}",
            source_type="xmind_import",
            status="active",
            created_by=created_by,
        )
        db.add(case_set)
        db.flush()

        xmind_file.case_set_id = case_set.case_set_id

        import_batch = XMindImportBatch(
            batch_uuid=str(uuid.uuid4()),
            xmind_file_id=xmind_file.xmind_file_id,
            case_set_id=case_set.case_set_id,
            import_status="pending",
            created_by=created_by,
        )
        db.add(import_batch)
        db.flush()

        node_count = import_topic_recursive(
            db=db,
            topic=root_topic,
            case_set_id=case_set.case_set_id,
            parent_id=None,
            import_batch_id=import_batch.import_batch_id,
            created_by=created_by,
            depth=1,
            sort_order=1,
        )

        import_batch.node_count = node_count
        import_batch.import_status = "success"
        xmind_file.process_status = "success"
        db.commit()

        return {
            "case_set_id": case_set.case_set_id,
            "xmind_file_id": xmind_file.xmind_file_id,
            "import_batch_id": import_batch.import_batch_id,
            "node_count": node_count,
            "message": "XMind导入成功",
        }
    except Exception as error:
        db.rollback()
        db.add(xmind_file)
        xmind_file.process_status = "failed"
        xmind_file.error_message = str(error)
        db.commit()
        raise HTTPException(status_code=400, detail=safe_xmind_error_message(error)) from error


def read_xmind_root_topic(file_path: Path) -> dict:
    try:
        with zipfile.ZipFile(file_path, "r") as xmind_zip:
            if "content.json" not in xmind_zip.namelist():
                raise ValueError("当前仅支持包含content.json的新版XMind文件")
            content_text = xmind_zip.read("content.json").decode("utf-8")
    except zipfile.BadZipFile as error:
        raise ValueError("上传文件不是有效的XMind压缩包") from error

    content = json.loads(content_text)
    if not isinstance(content, list) or not content:
        raise ValueError("content.json结构为空")

    root_topic = content[0].get("rootTopic")
    if not root_topic:
        raise ValueError("content.json中缺少rootTopic")

    return root_topic


def import_topic_recursive(
    db: Session,
    topic: dict,
    case_set_id: int,
    parent_id: int | None,
    import_batch_id: int,
    created_by: int,
    depth: int,
    sort_order: int,
) -> int:
    if depth > MAX_IMPORT_DEPTH:
        raise ValueError("XMind层级过深，导入终止")

    title = str(topic.get("title") or "未命名节点").strip()
    children = get_topic_children(topic)
    notes = read_topic_notes(topic)

    node = TestCaseNode(
        case_set_id=case_set_id,
        parent_id=parent_id,
        import_batch_id=import_batch_id,
        node_type="folder" if children else "case",
        title=title,
        precondition=None,
        test_steps=notes,
        expected_result=None,
        priority="P1",
        sort_order=sort_order,
        created_by=created_by,
    )
    db.add(node)
    db.flush()
    create_node_version(db, node, operation_type="create", operator_id=created_by, change_note="XMind导入创建节点")

    count = 1
    for index, child in enumerate(children, start=1):
        count += import_topic_recursive(
            db=db,
            topic=child,
            case_set_id=case_set_id,
            parent_id=node.node_id,
            import_batch_id=import_batch_id,
            created_by=created_by,
            depth=depth + 1,
            sort_order=index,
        )
    return count


def get_topic_children(topic: dict) -> list[dict]:
    children = topic.get("children") or {}
    attached = children.get("attached") or []
    return attached if isinstance(attached, list) else []


def read_topic_notes(topic: dict) -> str | None:
    notes = topic.get("notes")
    if not notes:
        return None
    plain = notes.get("plain") if isinstance(notes, dict) else None
    content = plain.get("content") if isinstance(plain, dict) else None
    return content if content else None


def export_case_set_to_xmind(
    db: Session,
    case_set_id: int,
    operator_id: int,
    node_tags_map: dict[int, list[str]] | None = None,
) -> Path:
    ensure_user_exists(db, operator_id)

    case_set = db.get(TestCaseSet, case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")

    nodes = list(
        db.scalars(
            select(TestCaseNode)
            .where(TestCaseNode.case_set_id == case_set_id, TestCaseNode.is_deleted == 0)
            .order_by(TestCaseNode.parent_id.asc(), TestCaseNode.sort_order.asc(), TestCaseNode.node_id.asc())
        ).all()
    )

    root_topic = build_export_root_topic(case_set, nodes, node_tags_map or {})
    workbook = [
        {
            "id": f"sheet-{case_set.case_set_id}",
            "class": "sheet",
            "title": case_set.name,
            "rootTopic": root_topic,
        }
    ]

    export_dir = Path(settings.export_root) / "xmind"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / f"case_set_{case_set_id}_{uuid.uuid4().hex}.xmind"

    with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as xmind_zip:
        xmind_zip.writestr("content.json", json.dumps(workbook, ensure_ascii=False, indent=2))
        xmind_zip.writestr("metadata.json", json.dumps({"creator": "rag_mindmap_platform"}, ensure_ascii=False))
        xmind_zip.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}}}, ensure_ascii=False))

    xmind_file = XMindFile(
        case_set_id=case_set_id,
        file_name=export_path.name,
        file_path=str(export_path),
        file_type="export",
        file_size=export_path.stat().st_size,
        process_status="success",
        created_by=operator_id,
    )
    db.add(xmind_file)
    db.commit()

    return export_path


def build_export_root_topic(case_set: TestCaseSet, nodes: list[TestCaseNode], node_tags_map: dict[int, list[str]]) -> dict:
    node_map = {node.node_id: node for node in nodes}
    children_map: dict[int | None, list[TestCaseNode]] = {}
    for node in nodes:
        parent_id = node.parent_id if node.parent_id in node_map else None
        children_map.setdefault(parent_id, []).append(node)

    root_children = [node_to_xmind_topic(node, children_map, node_tags_map) for node in children_map.get(None, [])]
    root_topic = {
        "id": f"case-set-{case_set.case_set_id}",
        "title": case_set.name,
    }
    if root_children:
        root_topic["children"] = {"attached": root_children}
    return root_topic


def node_to_xmind_topic(
    node: TestCaseNode,
    children_map: dict[int | None, list[TestCaseNode]],
    node_tags_map: dict[int, list[str]],
) -> dict:
    topic = {
        "id": f"node-{node.node_id}",
        "title": build_tagged_title(node.title, node_tags_map.get(node.node_id, [])),
    }

    note_lines = []
    if node.precondition:
        note_lines.append(f"前置条件：{node.precondition}")
    if node.test_steps:
        note_lines.append(f"测试步骤：{node.test_steps}")
    if node.expected_result:
        note_lines.append(f"预期结果：{node.expected_result}")
    if note_lines:
        topic["notes"] = {"plain": {"content": "\n".join(note_lines)}}

    children = [node_to_xmind_topic(child, children_map, node_tags_map) for child in children_map.get(node.node_id, [])]
    if children:
        topic["children"] = {"attached": children}
    return topic


def build_tagged_title(title: str, tags: list[str]) -> str:
    clean_tags = []
    for tag in tags:
        tag_text = str(tag or "").strip()
        if tag_text and tag_text not in clean_tags:
            clean_tags.append(tag_text)
    if not clean_tags:
        return title
    tag_prefix = "".join(f"【{tag}】" for tag in clean_tags)
    return f"{tag_prefix}{title}"


def safe_xmind_error_message(error: Exception) -> str:
    """把 XMind 导入的底层异常转成友好提示，避免回显服务器路径等敏感信息。"""
    if isinstance(error, HTTPException):
        return str(error.detail)
    text = str(error)
    if "content.json" in text and "仅支持" in text:
        return text
    if "不是有效的XMind压缩包" in text:
        return text
    if "层级过深" in text:
        return text
    if "content.json结构为空" in text or "缺少rootTopic" in text:
        return text
    return "XMind导入失败，请检查文件是否为新版 .xmind 格式（包含 content.json）"
