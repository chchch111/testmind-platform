"""重建演示测试数据：以“TestMind”本身为被测对象。

清空业务表后生成一套完整的演示数据：
- 6 个用户（覆盖 admin/manager/tester/executor 角色）
- 8 个用例集（脑图树，folder/case 两级，含前置/步骤/预期/优先级）
- 3 个知识库（各含 2~3 个手动知识来源）
- 2 个任务目录 + 4 个子任务 + 执行记录

运行方式：
  PYTHONPATH=backend .venv/Scripts/python.exe backend/scripts/reseed_platform_demo.py
"""
from pathlib import Path
import shutil

import bcrypt
import pymysql
from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
PROJECT_ROOT = BACKEND_DIR.parent

# 清空时遵循外键顺序，从子表到父表。
BUSINESS_TABLES = [
    "ai_generation_records",
    "rag_retrieval_records",
    "knowledge_chunks",
    "knowledge_sources",
    "faiss_indexes",
    "knowledge_bases",
    "test_execution_records",
    "test_task_assignees",
    "test_task_case_sets",
    "test_tasks",
    "test_case_node_versions",
    "test_case_nodes",
    "xmind_import_batches",
    "xmind_files",
    "case_node_metas",
    "case_set_snapshots",
    "case_set_reviews",
    "test_case_sets",
    "users",
]

PASSWORD_HASH = bcrypt.hashpw("admin123456".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

USERS = [
    ("admin", "系统管理员", "admin"),
    ("manager01", "测试经理", "manager"),
    ("tester01", "测试工程师小李", "tester"),
    ("tester02", "测试工程师小王", "tester"),
    ("executor01", "执行人小赵", "executor"),
    ("executor02", "执行人小钱", "executor"),
]

# 用例集定义：name -> {description, source_type, nodes: [ {title, node_type, children?} ] }
# node: title + node_type; case 节点可带 precondition/test_steps/expected_result/priority
CASE_SETS = [
    {
        "name": "用户登录与权限管理测试",
        "description": "覆盖平台登录、角色权限、账号管理功能的测试用例，验证不同角色访问控制是否正确。",
        "nodes": [
            {
                "title": "登录功能",
                "node_type": "folder",
                "children": [
                    {
                        "title": "正确账号密码登录成功",
                        "node_type": "case", "priority": "P0",
                        "precondition": "已创建 admin/admin123456 账号",
                        "test_steps": "1. 打开登录页\n2. 输入用户名 admin\n3. 输入密码 admin123456\n4. 点击登录",
                        "expected_result": "登录成功，跳转系统首页，侧边栏显示全部菜单",
                    },
                    {
                        "title": "密码错误登录失败",
                        "node_type": "case", "priority": "P1",
                        "precondition": "无",
                        "test_steps": "1. 输入正确用户名\n2. 输入错误密码\n3. 点击登录",
                        "expected_result": "提示“用户名或密码错误”，停留在登录页",
                    },
                    {
                        "title": "未登录访问受保护页面被拦截",
                        "node_type": "case", "priority": "P1",
                        "precondition": "浏览器无登录态",
                        "test_steps": "1. 直接访问 /case-sets\n2. 观察路由跳转",
                        "expected_result": "跳转登录页，并携带 redirect 参数，登录后回跳原页面",
                    },
                    {
                        "title": "退出登录清除登录态",
                        "node_type": "case", "priority": "P2",
                        "precondition": "已登录",
                        "test_steps": "1. 点击右上角退出登录\n2. 返回首页",
                        "expected_result": "跳转登录页，localStorage 中的 token 被清除",
                    },
                ],
            },
            {
                "title": "权限控制",
                "node_type": "folder",
                "children": [
                    {
                        "title": "非管理员访问权限管理被拒绝",
                        "node_type": "case", "priority": "P0",
                        "precondition": "使用 tester 角色账号登录",
                        "test_steps": "1. 直接访问 /permissions 路由",
                        "expected_result": "跳转 403 无权限页面",
                    },
                    {
                        "title": "管理员新增用户",
                        "node_type": "case", "priority": "P1",
                        "precondition": "admin 登录",
                        "test_steps": "1. 进入权限管理\n2. 点击新增用户\n3. 填写用户名/角色\n4. 保存",
                        "expected_result": "用户创建成功，可用新账号登录",
                    },
                    {
                        "title": "管理员重置用户密码",
                        "node_type": "case", "priority": "P2",
                        "precondition": "admin 登录，存在普通用户",
                        "test_steps": "1. 权限管理选择用户\n2. 点击重置密码\n3. 设置新密码",
                        "expected_result": "重置成功，该用户可用新密码登录",
                    },
                ],
            },
        ],
    },
    {
        "name": "用例集管理功能测试",
        "description": "覆盖用例集创建、列表查询、发布、删除等管理功能的测试用例。",
        "nodes": [
            {
                "title": "用例集创建",
                "node_type": "folder",
                "children": [
                    {
                        "title": "创建草稿用例集",
                        "node_type": "case", "priority": "P0",
                        "precondition": "已登录",
                        "test_steps": "1. 进入用例集管理\n2. 点击新建\n3. 填写名称与描述\n4. 保存",
                        "expected_result": "创建成功，状态为草稿，出现在列表",
                    },
                    {
                        "title": "名称为空时拒绝创建",
                        "node_type": "case", "priority": "P2",
                        "precondition": "已登录",
                        "test_steps": "1. 新建用例集\n2. 名称留空\n3. 保存",
                        "expected_result": "提示“请填写名称”，不创建",
                    },
                ],
            },
            {
                "title": "用例集发布与状态",
                "node_type": "folder",
                "children": [
                    {
                        "title": "草稿发布为有效",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在草稿用例集",
                        "test_steps": "1. 打开草稿用例集\n2. 点击发布",
                        "expected_result": "状态变为 active，可被任务创建和知识库导入选用",
                    },
                    {
                        "title": "列表分页与关键字过滤",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在多条用例集",
                        "test_steps": "1. 在列表页输入关键字\n2. 观察过滤结果\n3. 翻页",
                        "expected_result": "关键字过滤生效，分页正确",
                    },
                    {
                        "title": "删除用例集级联清理",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在带节点的用例集",
                        "test_steps": "1. 删除用例集\n2. 确认弹窗\n3. 重新打开",
                        "expected_result": "用例集及其节点、脑图元数据、快照、评审记录被清理",
                    },
                ],
            },
            {
                "title": "JSON导出",
                "node_type": "folder",
                "children": [
                    {
                        "title": "导出用例集JSON",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在 active 用例集",
                        "test_steps": "1. 列表选择导出JSON\n2. 下载文件\n3. 检查内容",
                        "expected_result": "下载的 JSON 含用例集元信息与完整树结构",
                    },
                ],
            },
        ],
    },
    {
        "name": "思维导图编辑器测试",
        "description": "覆盖脑图节点的增删改、拖拽、标签、层级等编辑功能的测试用例。",
        "nodes": [
            {
                "title": "节点编辑",
                "node_type": "folder",
                "children": [
                    {
                        "title": "新增根节点与子节点",
                        "node_type": "case", "priority": "P0",
                        "precondition": "打开用例集详情",
                        "test_steps": "1. 点击新增根节点\n2. 填写标题保存\n3. 选中后新增子节点",
                        "expected_result": "节点正确插入树结构，可继续添加下级",
                    },
                    {
                        "title": "编辑节点内容",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在用例节点",
                        "test_steps": "1. 双击节点标题\n2. 修改标题\n3. 保存",
                        "expected_result": "标题更新，生成节点历史版本",
                    },
                    {
                        "title": "右键菜单删除节点",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在叶子节点",
                        "test_steps": "1. 右键节点\n2. 环形菜单点删除\n3. 确认",
                        "expected_result": "节点被删除，子节点一并处理",
                    },
                ],
            },
            {
                "title": "脑图操作",
                "node_type": "folder",
                "children": [
                    {
                        "title": "框选批量标记",
                        "node_type": "case", "priority": "P1",
                        "precondition": "脑图有多个节点",
                        "test_steps": "1. 空白处拖拽框选\n2. 右键其中一点\n3. 选择批量操作",
                        "expected_result": "框选的全部 case 节点被批量应用操作",
                    },
                    {
                        "title": "迷你地图拖拽定位",
                        "node_type": "case", "priority": "P2",
                        "precondition": "脑图可滚动",
                        "test_steps": "1. 在迷你地图红框上拖拽\n2. 观察主画布",
                        "expected_result": "主画布视野随迷你地图红框移动",
                    },
                    {
                        "title": "撤销与重做",
                        "node_type": "case", "priority": "P2",
                        "precondition": "有编辑操作",
                        "test_steps": "1. 执行节点操作\n2. 点撤销\n3. 点重做",
                        "expected_result": "操作被正确撤销与重做",
                    },
                ],
            },
            {
                "title": "标签与外观",
                "node_type": "folder",
                "children": [
                    {
                        "title": "给节点打标签",
                        "node_type": "case", "priority": "P2",
                        "precondition": "选中一个节点",
                        "test_steps": "1. 工具栏选择系统/业务标签\n2. 点击标签",
                        "expected_result": "标签出现在节点上，可后续按标签筛选",
                    },
                    {
                        "title": "按标签筛选节点",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在带标签节点",
                        "test_steps": "1. 打开标签筛选下拉\n2. 选择标签",
                        "expected_result": "脑图仅显示命中标签的节点",
                    },
                ],
            },
        ],
    },
    {
        "name": "知识库与RAG检索测试",
        "description": "覆盖知识库增删改、知识来源管理、FAISS索引构建与检索的测试用例。",
        "nodes": [
            {
                "title": "知识库管理",
                "node_type": "folder",
                "children": [
                    {
                        "title": "创建知识库",
                        "node_type": "case", "priority": "P0",
                        "precondition": "已登录",
                        "test_steps": "1. 知识库页点新建\n2. 填写名称/产品类型/模块\n3. 保存",
                        "expected_result": "知识库创建成功，出现在左侧列表",
                    },
                    {
                        "title": "编辑知识库信息",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在知识库",
                        "test_steps": "1. 列表点编辑\n2. 修改描述/状态\n3. 保存",
                        "expected_result": "信息更新，列表实时刷新",
                    },
                    {
                        "title": "删除知识库级联清理",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在带来源与索引的知识库",
                        "test_steps": "1. 删除知识库\n2. 确认",
                        "expected_result": "来源、切片、FAISS 文件一并清理",
                    },
                ],
            },
            {
                "title": "知识来源",
                "node_type": "folder",
                "children": [
                    {
                        "title": "手动粘贴知识来源",
                        "node_type": "case", "priority": "P0",
                        "precondition": "选中知识库",
                        "test_steps": "1. 手动粘贴Tab\n2. 填写名称与正文\n3. 保存",
                        "expected_result": "来源创建成功，可在列表中查看",
                    },
                    {
                        "title": "上传文档作为知识来源",
                        "node_type": "case", "priority": "P1",
                        "precondition": "有 .txt/.md/.xmind 文件",
                        "test_steps": "1. 上传文件Tab\n2. 拖拽或选择文件\n3. 上传解析",
                        "expected_result": "文件被解析为纯文本来源",
                    },
                    {
                        "title": "查看来源正文",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在来源",
                        "test_steps": "1. 来源列表点查看\n2. 检查弹窗",
                        "expected_result": "弹窗展示来源名称、类型、完整正文",
                    },
                ],
            },
            {
                "title": "索引与检索",
                "node_type": "folder",
                "children": [
                    {
                        "title": "构建FAISS索引显示真实进度",
                        "node_type": "case", "priority": "P0",
                        "precondition": "知识库存在来源",
                        "test_steps": "1. 构建索引Tab\n2. 点击构建\n3. 观察进度条",
                        "expected_result": "进度条从 0 到 100 实时推进，完成后索引状态为可用",
                    },
                    {
                        "title": "RAG检索命中相关知识",
                        "node_type": "case", "priority": "P0",
                        "precondition": "索引已构建",
                        "test_steps": "1. RAG检索Tab\n2. 输入问题\n3. 开始检索",
                        "expected_result": "返回带来源名与相似度的知识片段",
                    },
                    {
                        "title": "未构建索引时检索报友好提示",
                        "node_type": "case", "priority": "P2",
                        "precondition": "知识库无索引",
                        "test_steps": "1. 在未构建索引的库检索",
                        "expected_result": "提示“请先构建索引”，不报底层错误",
                    },
                ],
            },
        ],
    },
    {
        "name": "AI生成用例功能测试",
        "description": "覆盖AI生成用例的参数配置、生成链路、结果入库与追溯的测试用例。",
        "nodes": [
            {
                "title": "生成参数",
                "node_type": "folder",
                "children": [
                    {
                        "title": "选择知识库与需求文本生成",
                        "node_type": "case", "priority": "P0",
                        "precondition": "存在已构建索引的知识库",
                        "test_steps": "1. AI生成页\n2. 选择知识库\n3. 输入测试需求\n4. 开始生成",
                        "expected_result": "生成成功，结果在右侧预览，进度状态条正常",
                    },
                    {
                        "title": "未选知识库时拦截",
                        "node_type": "case", "priority": "P1",
                        "precondition": "无",
                        "test_steps": "1. 清空知识库选择\n2. 点击开始生成",
                        "expected_result": "提示“请先选择知识库”",
                    },
                ],
            },
            {
                "title": "生成结果",
                "node_type": "folder",
                "children": [
                    {
                        "title": "自动入库为草稿用例集",
                        "node_type": "case", "priority": "P1",
                        "precondition": "开启自动入库",
                        "test_steps": "1. 生成成功\n2. 打开生成的脑图",
                        "expected_result": "生成结果保存为草稿用例集，可在用例集管理看到并发布",
                    },
                    {
                        "title": "生成记录可回看与追溯",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在生成记录",
                        "test_steps": "1. 最近生成记录\n2. 点详情",
                        "expected_result": "展示需求、模型、使用的知识片段ID、生成JSON",
                    },
                ],
            },
        ],
    },
    {
        "name": "测试任务与执行工作台测试",
        "description": "覆盖任务目录、子任务、执行人认领与用例执行的测试用例。",
        "nodes": [
            {
                "title": "任务管理",
                "node_type": "folder",
                "children": [
                    {
                        "title": "创建任务目录并添加子任务",
                        "node_type": "case", "priority": "P0",
                        "precondition": "存在 active 用例集与用户",
                        "test_steps": "1. 任务管理创建目录\n2. 目录下添加子任务\n3. 选用例集与执行人",
                        "expected_result": "目录与子任务创建成功，子任务关联用例集",
                    },
                    {
                        "title": "子任务认领",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在已分配子任务",
                        "test_steps": "1. 执行人进入执行工作台\n2. 点认领任务",
                        "expected_result": "认领成功，状态从待认领变已认领",
                    },
                ],
            },
            {
                "title": "用例执行",
                "node_type": "folder",
                "children": [
                    {
                        "title": "脑图标记用例通过",
                        "node_type": "case", "priority": "P0",
                        "precondition": "任务已认领，有执行记录",
                        "test_steps": "1. 进入子任务执行页\n2. 右键case节点\n3. 环形菜单点通过",
                        "expected_result": "节点状态变绿，顶部进度条与统计实时更新",
                    },
                    {
                        "title": "登记缺陷标记失败",
                        "node_type": "case", "priority": "P1",
                        "precondition": "任务已认领",
                        "test_steps": "1. 右键case节点\n2. 点缺陷\n3. 填写缺陷描述",
                        "expected_result": "节点标记失败并登记缺陷，报告可汇总",
                    },
                    {
                        "title": "目录节点级联操作下级用例",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在目录下多个用例",
                        "test_steps": "1. 右键目录节点\n2. 选择状态",
                        "expected_result": "该目录下所有子用例统一标记",
                    },
                ],
            },
        ],
    },
    {
        "name": "版本快照与用例评审测试",
        "description": "覆盖脑图版本快照、节点历史版本、用例集评审的测试用例。",
        "nodes": [
            {
                "title": "版本快照",
                "node_type": "folder",
                "children": [
                    {
                        "title": "创建脑图版本快照",
                        "node_type": "case", "priority": "P1",
                        "precondition": "打开用例集",
                        "test_steps": "1. 点击创建版本\n2. 命名快照",
                        "expected_result": "快照保存，可在版本快照弹窗看到",
                    },
                    {
                        "title": "恢复快照覆盖脑图",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在快照",
                        "test_steps": "1. 版本快照弹窗\n2. 点恢复\n3. 确认",
                        "expected_result": "脑图标签、备注、链接、外观被快照内容覆盖",
                    },
                ],
            },
            {
                "title": "用例评审",
                "node_type": "folder",
                "children": [
                    {
                        "title": "发起用例集评审",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在 active 用例集",
                        "test_steps": "1. 点发起用例评审\n2. 选评审人\n3. 提交",
                        "expected_result": "评审记录创建，状态为待评审",
                    },
                    {
                        "title": "完成评审填写结论",
                        "node_type": "case", "priority": "P2",
                        "precondition": "存在待评审记录",
                        "test_steps": "1. 开始评审\n2. 完成评审\n3. 填结论",
                        "expected_result": "评审状态流转为已完成，结论被保存",
                    },
                ],
            },
        ],
    },
    {
        "name": "XMind导入导出功能测试",
        "description": "覆盖XMind文件导入、导出及错误处理的测试用例。",
        "nodes": [
            {
                "title": "XMind导入",
                "node_type": "folder",
                "children": [
                    {
                        "title": "导入新版XMind文件",
                        "node_type": "case", "priority": "P0",
                        "precondition": "有包含 content.json 的 .xmind 文件",
                        "test_steps": "1. 用例集页导入XMind\n2. 选择文件\n3. 上传",
                        "expected_result": "导入成功，生成用例集并解析出树形节点",
                    },
                    {
                        "title": "非法文件导入报友好错误",
                        "node_type": "case", "priority": "P2",
                        "precondition": "有非XMind文件",
                        "test_steps": "1. 上传非XMind文件\n2. 观察提示",
                        "expected_result": "提示“不是有效的XMind压缩包”，不暴露底层路径",
                    },
                ],
            },
            {
                "title": "XMind导出",
                "node_type": "folder",
                "children": [
                    {
                        "title": "导出用例集为XMind",
                        "node_type": "case", "priority": "P1",
                        "precondition": "存在 active 用例集",
                        "test_steps": "1. 选择导出XMind\n2. 下载",
                        "expected_result": "导出含标签的 .xmind 文件，可用XMind打开",
                    },
                ],
            },
        ],
    },
]

# 知识库定义：name -> {description, product_type, hardware_module, sources: [{source_name, content_text}]}
KNOWLEDGE_BASES = [
    {
        "name": "平台产品功能知识库",
        "description": "平台各功能模块的产品说明与使用规范，用于RAG检索辅助AI生成测试用例。",
        "product_type": "web_platform",
        "hardware_module": "function_module",
        "sources": [
            {
                "source_name": "平台功能模块说明",
                "content_text": (
                    "TestMind智能测试用例全生命周期管理平台包含以下核心功能模块：\n"
                    "1. 用例集管理：支持手动创建、XMind导入、AI生成三种来源，用例集可发布为active供任务选用。\n"
                    "2. 思维导图编辑器：节点分目录和用例两类，支持增删改、拖拽、标签、备注、链接、图片、撤销重做、迷你地图。\n"
                    "3. 知识库管理：集中管理测试资料，支持手动粘贴、文件上传、从用例集导入，构建FAISS向量索引。\n"
                    "4. AI生成用例：结合RAG检索的知识片段与用户需求文本，调用DeepSeek生成树形测试用例并自动入库。\n"
                    "5. 测试任务：任务分目录和子任务两级，子任务关联用例集并分配执行人，执行人认领后在工作台执行。\n"
                    "6. 版本快照与评审：支持脑图版本快照、节点历史版本回退、用例集评审闭环。\n"
                    "7. 权限管理：管理员可管理用户账号与角色，非管理员访问受保护路由会被拒绝。"
                ),
            },
            {
                "source_name": "平台登录与权限说明",
                "content_text": (
                    "平台支持四种角色：admin管理员、manager管理人员、tester测试人员、executor执行人员。\n"
                    "管理员可进入权限管理模块新增用户、重置密码；非管理员直接访问权限管理路由会跳转403。\n"
                    "登录采用token认证，未登录访问受保护页面会跳转登录页并携带redirect参数，登录后回跳。\n"
                    "开发演示账号为admin/admin123456。"
                ),
            },
            {
                "source_name": "AI生成与RAG链路说明",
                "content_text": (
                    "AI生成用例的处理链路为：选择知识库→RAG检索相似知识片段→结合需求文本调用DeepSeek生成树形用例→自动保存为草稿用例集。\n"
                    "RAG检索使用bge-small-zh向量模型对知识库来源切片后构建FAISS索引，检索时返回带相似度分数的知识片段。\n"
                    "生成记录保存在最近生成列表中，可回看原始需求、模型、使用的知识片段和生成JSON，实现需求到用例全链路可追溯。"
                ),
            },
        ],
    },
    {
        "name": "测试规范与经验知识库",
        "description": "沉淀平台自身的测试规范、用例编写规范与回归测试经验。",
        "product_type": "web_platform",
        "hardware_module": "qa_practice",
        "sources": [
            {
                "source_name": "平台测试规范",
                "content_text": (
                    "平台测试遵循以下规范：\n"
                    "1. 用例优先级：P0为阻断性功能必须验证，P1为核心功能，P2为一般功能，P3为边缘场景。\n"
                    "2. 用例编写：每条用例应包含标题、前置条件、测试步骤、预期结果四要素。\n"
                    "3. 执行状态：通过passed、失败failed、阻塞blocked、不适用skipped、未执行not_run。\n"
                    "4. 缺陷管理：执行失败时登记缺陷描述，最终任务报告按执行人汇总通过率与缺陷清单。\n"
                    "5. 评审闭环：用例集评审状态从待评审流转到评审中再到已完成，完成后填写评审结论。"
                ),
            },
            {
                "source_name": "历史回归经验",
                "content_text": (
                    "回归测试重点场景：\n"
                    "1. 权限变化后验证非管理员访问被拒绝的路径。\n"
                    "2. 知识库重新构建索引后验证RAG检索结果正确性。\n"
                    "3. 任务认领后验证未认领时无法提交执行结果。\n"
                    "4. 删除用例集后验证关联的快照、评审、脑图元数据被清理。\n"
                    "5. 前端打包优化后验证各页面按需加载正常，首屏性能达标。"
                ),
            },
        ],
    },
    {
        "name": "缺陷与边界场景知识库",
        "description": "记录平台历史缺陷与边界场景，辅助AI生成更全面的用例。",
        "product_type": "web_platform",
        "hardware_module": "edge_case",
        "sources": [
            {
                "source_name": "历史缺陷记录",
                "content_text": (
                    "历史发现的典型缺陷：\n"
                    "1. 删除用例集接口要求body导致前端无body删除返回422。\n"
                    "2. 构建索引批量flush时出现index变量遮蔽导致向量维度错误。\n"
                    "3. 执行任务列表存在N+1查询导致响应慢，后优化为一次查询。\n"
                    "4. 前端入口bundle过大，后通过按需引入降低首屏加载。\n"
                    "5. 框选批量标记目录节点时未级联到子用例。"
                ),
            },
            {
                "source_name": "边界场景说明",
                "content_text": (
                    "需要覆盖的边界场景：\n"
                    "1. 用例集名称超长、特殊字符处理。\n"
                    "2. 知识库上传超过20MB文件的拦截提示。\n"
                    "3. RAG检索top_k设置最大20条时的分页行为。\n"
                    "4. 脑图节点层级过深时的展开与迷你地图展示。\n"
                    "5. 同时标记多个节点状态时的并发同步版本号冲突处理。"
                ),
            },
        ],
    },
]

# 任务定义：目录 -> [子任务]
# subtask: {task_name, case_set_name, owner, assignees, status}
TASK_DIRECTORIES = [
    {
        "task_name": "平台功能回归测试",
        "subtasks": [
            {
                "task_name": "用户与权限回归",
                "case_set_name": "用户登录与权限管理测试",
                "owner": "manager01",
                "assignees": ["executor01"],
                "status": "running",
                "executions": {"正确账号密码登录成功": "passed", "密码错误登录失败": "passed", "非管理员访问权限管理被拒绝": "failed"},
            },
            {
                "task_name": "用例集与脑图回归",
                "case_set_name": "用例集管理功能测试",
                "owner": "manager01",
                "assignees": ["executor01"],
                "status": "running",
                "executions": {"创建草稿用例集": "passed", "草稿发布为有效": "passed"},
            },
        ],
    },
    {
        "task_name": "AI与知识库验收",
        "subtasks": [
            {
                "task_name": "知识库与RAG验收",
                "case_set_name": "知识库与RAG检索测试",
                "owner": "manager01",
                "assignees": ["executor02"],
                "status": "assigned",
                "executions": {},
            },
            {
                "task_name": "AI生成用例验收",
                "case_set_name": "AI生成用例功能测试",
                "owner": "manager01",
                "assignees": ["executor02"],
                "status": "assigned",
                "executions": {},
            },
        ],
    },
]


def get_config() -> dict:
    return dotenv_values(ENV_FILE)


def connect() -> pymysql.connections.Connection:
    config = get_config()
    return pymysql.connect(
        host=config.get("MYSQL_HOST", "127.0.0.1"),
        port=int(config.get("MYSQL_PORT", 3306)),
        user=config.get("MYSQL_USER", "root"),
        password=config.get("MYSQL_PASSWORD", ""),
        database=config.get("MYSQL_DATABASE", "rag_mindmap_test_platform"),
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def cleanup_storage() -> None:
    """清理 FAISS 索引文件，避免残留旧知识库的索引。"""
    faiss_root = PROJECT_ROOT / "storage" / "faiss"
    if faiss_root.exists():
        shutil.rmtree(faiss_root, ignore_errors=True)
        faiss_root.mkdir(parents=True, exist_ok=True)
        print("已清理 storage/faiss 下的索引文件")


def insert_users(cur) -> dict:
    """插入用户，返回 username -> user_id 映射。"""
    mapping = {}
    for index, (username, real_name, role_code) in enumerate(USERS, start=1):
        cur.execute(
            "INSERT INTO users (user_id, username, password_hash, real_name, role_code, email) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (index, username, PASSWORD_HASH, real_name, role_code, f"{username}@example.com"),
        )
        mapping[username] = index
    return mapping


def insert_case_sets(cur, user_id_map: dict) -> dict:
    """插入用例集与节点树，返回 case_set_name -> case_set_id 映射。"""
    case_set_map = {}
    case_set_id = 1
    node_id = 1
    for case_set in CASE_SETS:
        cur.execute(
            "INSERT INTO test_case_sets (case_set_id, name, description, source_type, status, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (case_set_id, case_set["name"], case_set["description"], "manual", "active", user_id_map["admin"]),
        )
        case_set_map[case_set["name"]] = case_set_id

        for folder in case_set["nodes"]:
            # 插入目录节点
            cur.execute(
                "INSERT INTO test_case_nodes (node_id, case_set_id, parent_id, node_type, title, priority, sort_order, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (node_id, case_set_id, None, "folder", folder["title"], "P1", 0, user_id_map["admin"]),
            )
            folder_id = node_id
            node_id += 1
            # 插入子用例节点
            for sort_index, child in enumerate(folder.get("children", []), start=1):
                cur.execute(
                    "INSERT INTO test_case_nodes "
                    "(node_id, case_set_id, parent_id, node_type, title, precondition, test_steps, expected_result, priority, sort_order, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        node_id,
                        case_set_id,
                        folder_id,
                        child["node_type"],
                        child["title"],
                        child.get("precondition"),
                        child.get("test_steps"),
                        child.get("expected_result"),
                        child.get("priority", "P1"),
                        sort_index,
                        user_id_map["admin"],
                    ),
                )
                node_id += 1

        case_set_id += 1

    return case_set_map


def insert_knowledge_bases(cur, user_id_map: dict) -> dict:
    """插入知识库与来源，返回 knowledge_base_name -> knowledge_base_id 映射。"""
    kb_map = {}
    kb_id = 1
    source_id = 1
    for kb in KNOWLEDGE_BASES:
        cur.execute(
            "INSERT INTO knowledge_bases (knowledge_base_id, name, description, product_type, hardware_module, status, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (kb_id, kb["name"], kb["description"], kb["product_type"], kb["hardware_module"], "active", user_id_map["admin"]),
        )
        kb_map[kb["name"]] = kb_id
        for source in kb["sources"]:
            cur.execute(
                "INSERT INTO knowledge_sources (source_id, knowledge_base_id, source_name, source_type, content_text, status, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (source_id, kb_id, source["source_name"], "manual_text", source["content_text"], "active", user_id_map["admin"]),
            )
            source_id += 1
        kb_id += 1
    return kb_map


def insert_tasks(cur, user_id_map: dict, case_set_map: dict) -> dict:
    """插入任务目录、子任务、执行记录。返回 task_name -> task_id 映射。"""
    task_id = 1
    execution_id = 1
    node_id_by_title = {}  # (case_set_name, title) -> node_id

    # 先建 node 标题索引，便于执行记录关联
    cur.execute("SELECT node_id, case_set_id, title FROM test_case_nodes WHERE node_type='case'")
    for row in cur.fetchall():
        node_id_by_title[(row["case_set_id"], row["title"])] = row["node_id"]

    for directory in TASK_DIRECTORIES:
        # 目录任务
        cur.execute(
            "INSERT INTO test_tasks (task_id, parent_id, task_name, owner_id, status, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (task_id, None, directory["task_name"], user_id_map[directory.get("owner", "manager01")], "assigned", user_id_map["admin"]),
        )
        directory_id = task_id
        task_id += 1

        for subtask in directory["subtasks"]:
            cur.execute(
                "INSERT INTO test_tasks (task_id, parent_id, task_name, owner_id, status, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (task_id, directory_id, subtask["task_name"], user_id_map[subtask["owner"]], subtask["status"], user_id_map["admin"]),
            )
            subtask_id = task_id
            task_id += 1

            case_set_id = case_set_map[subtask["case_set_name"]]
            # 任务-用例集关联
            cur.execute(
                "INSERT INTO test_task_case_sets (task_id, case_set_id) VALUES (%s, %s)",
                (subtask_id, case_set_id),
            )
            # 执行人
            for assignee in subtask["assignees"]:
                cur.execute(
                    "INSERT INTO test_task_assignees (task_id, assignee_id, assign_status) VALUES (%s, %s, %s)",
                    (subtask_id, user_id_map[assignee], "accepted" if subtask["status"] == "running" else "assigned"),
                )

            # 执行记录（基于 execution 状态映射）
            executions = subtask.get("executions", {})
            for title, status in executions.items():
                node_id = node_id_by_title.get((case_set_id, title))
                if not node_id:
                    continue
                cur.execute(
                    "INSERT INTO test_execution_records "
                    "(execution_id, task_id, case_node_id, executor_id, execution_status, actual_result, sync_version, executed_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())",
                    (
                        execution_id,
                        subtask_id,
                        node_id,
                        user_id_map[subtask["assignees"][0]],
                        status,
                        "执行通过，实际结果符合预期。" if status == "passed" else "执行失败，实际结果不符合预期。",
                        1,
                    ),
                )
                execution_id += 1

    return {}


def reseed() -> None:
    print("开始重建演示数据（以本平台为被测对象）...")
    cleanup_storage()

    connection = connect()
    try:
        with connection.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in BUSINESS_TABLES:
                cur.execute(f"TRUNCATE TABLE {table}")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            print(f"已清空 {len(BUSINESS_TABLES)} 张业务表")

            user_id_map = insert_users(cur)
            print(f"已生成 {len(user_id_map)} 个用户")

            case_set_map = insert_case_sets(cur, user_id_map)
            print(f"已生成 {len(case_set_map)} 个用例集")

            kb_map = insert_knowledge_bases(cur, user_id_map)
            print(f"已生成 {len(kb_map)} 个知识库")

            insert_tasks(cur, user_id_map, case_set_map)
            print("已生成任务目录、子任务与执行记录")

        connection.commit()
        print("数据重建完成！")
    except Exception as error:
        connection.rollback()
        raise error
    finally:
        connection.close()


if __name__ == "__main__":
    reseed()
