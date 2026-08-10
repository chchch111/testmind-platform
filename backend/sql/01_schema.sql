CREATE DATABASE IF NOT EXISTS rag_mindmap_test_platform
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

USE rag_mindmap_test_platform;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS ai_generation_records;
DROP TABLE IF EXISTS rag_retrieval_records;
DROP TABLE IF EXISTS knowledge_chunks;
DROP TABLE IF EXISTS knowledge_sources;
DROP TABLE IF EXISTS faiss_indexes;
DROP TABLE IF EXISTS knowledge_bases;
DROP TABLE IF EXISTS test_execution_records;
DROP TABLE IF EXISTS test_task_assignees;
DROP TABLE IF EXISTS test_task_case_sets;
DROP TABLE IF EXISTS test_tasks;
DROP TABLE IF EXISTS test_case_node_versions;
DROP TABLE IF EXISTS test_case_nodes;
DROP TABLE IF EXISTS xmind_import_batches;
DROP TABLE IF EXISTS xmind_files;
DROP TABLE IF EXISTS test_case_sets;
DROP TABLE IF EXISTS case_node_metas;
DROP TABLE IF EXISTS case_set_snapshots;
DROP TABLE IF EXISTS case_set_reviews;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
    user_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希值',
    real_name VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
    role_code VARCHAR(30) NOT NULL DEFAULT 'tester' COMMENT '角色编码：admin/manager/tester/executor',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    phone VARCHAR(30) DEFAULT NULL COMMENT '手机号',
    is_active TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_users_role_code (role_code),
    INDEX idx_users_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

CREATE TABLE test_case_sets (
    case_set_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用例集ID',
    name VARCHAR(200) NOT NULL COMMENT '用例集名称',
    description TEXT DEFAULT NULL COMMENT '用例集说明',
    source_type VARCHAR(30) NOT NULL DEFAULT 'manual' COMMENT '来源：manual/xmind_import/ai_generated',
    status VARCHAR(30) NOT NULL DEFAULT 'active' COMMENT '状态：active/archived/disabled',
    created_by BIGINT NOT NULL COMMENT '创建人ID',
    updated_by BIGINT DEFAULT NULL COMMENT '更新人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_case_sets_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_case_sets_updated_by FOREIGN KEY (updated_by) REFERENCES users(user_id),
    INDEX idx_case_sets_name (name),
    INDEX idx_case_sets_status (status),
    INDEX idx_case_sets_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试用例集表';

CREATE TABLE xmind_files (
    xmind_file_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'XMind文件ID',
    case_set_id BIGINT DEFAULT NULL COMMENT '关联用例集ID',
    file_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '本地文件路径',
    storage_type VARCHAR(30) NOT NULL DEFAULT 'local' COMMENT '存储类型：local/object_storage',
    storage_key VARCHAR(500) DEFAULT NULL COMMENT '对象存储Key，预留云端扩展',
    file_type VARCHAR(30) NOT NULL COMMENT '文件类型：import/export',
    file_size BIGINT DEFAULT NULL COMMENT '文件大小',
    process_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT '处理状态：pending/success/failed',
    error_message TEXT DEFAULT NULL COMMENT '失败原因',
    created_by BIGINT NOT NULL COMMENT '操作人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_xmind_files_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE SET NULL,
    CONSTRAINT fk_xmind_files_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    INDEX idx_xmind_files_case_set_id (case_set_id),
    INDEX idx_xmind_files_file_type (file_type),
    INDEX idx_xmind_files_process_status (process_status),
    INDEX idx_xmind_files_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='XMind文件记录表';

CREATE TABLE xmind_import_batches (
    import_batch_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '导入批次ID',
    batch_uuid CHAR(36) NOT NULL UNIQUE COMMENT '导入批次UUID',
    xmind_file_id BIGINT NOT NULL COMMENT '关联XMind文件ID',
    case_set_id BIGINT NOT NULL COMMENT '导入生成的用例集ID',
    node_count INT NOT NULL DEFAULT 0 COMMENT '本批次导入节点数量',
    import_status VARCHAR(30) NOT NULL DEFAULT 'pending' COMMENT '导入状态：pending/success/failed/rolled_back',
    error_message TEXT DEFAULT NULL COMMENT '失败原因',
    created_by BIGINT NOT NULL COMMENT '导入人ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_import_batches_xmind_file FOREIGN KEY (xmind_file_id) REFERENCES xmind_files(xmind_file_id),
    CONSTRAINT fk_import_batches_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE CASCADE,
    CONSTRAINT fk_import_batches_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    INDEX idx_import_batches_case_set_id (case_set_id),
    INDEX idx_import_batches_status (import_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='XMind导入批次表';

CREATE TABLE test_case_nodes (
    node_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '节点ID',
    case_set_id BIGINT NOT NULL COMMENT '所属用例集ID',
    parent_id BIGINT DEFAULT NULL COMMENT '父节点ID',
    import_batch_id BIGINT DEFAULT NULL COMMENT 'XMind导入批次ID，手动创建为空',
    node_type VARCHAR(30) NOT NULL DEFAULT 'folder' COMMENT '节点类型：folder/case',
    title VARCHAR(300) NOT NULL COMMENT '节点标题',
    precondition TEXT DEFAULT NULL COMMENT '前置条件',
    test_steps TEXT DEFAULT NULL COMMENT '测试步骤',
    expected_result TEXT DEFAULT NULL COMMENT '预期结果',
    priority VARCHAR(20) NOT NULL DEFAULT 'P1' COMMENT '优先级：P0/P1/P2/P3',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '同级排序',
    created_by BIGINT NOT NULL COMMENT '创建人ID',
    updated_by BIGINT DEFAULT NULL COMMENT '更新人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_case_nodes_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_nodes_parent FOREIGN KEY (parent_id) REFERENCES test_case_nodes(node_id) ON DELETE SET NULL,
    CONSTRAINT fk_case_nodes_import_batch FOREIGN KEY (import_batch_id) REFERENCES xmind_import_batches(import_batch_id) ON DELETE SET NULL,
    CONSTRAINT fk_case_nodes_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_case_nodes_updated_by FOREIGN KEY (updated_by) REFERENCES users(user_id),
    INDEX idx_case_nodes_case_set_parent (case_set_id, parent_id),
    INDEX idx_case_nodes_case_set_priority (case_set_id, priority),
    INDEX idx_case_nodes_case_set_sort (case_set_id, sort_order),
    INDEX idx_case_nodes_import_batch_id (import_batch_id),
    INDEX idx_case_nodes_node_type (node_type),
    INDEX idx_case_nodes_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='思维导图测试用例节点表';

CREATE TABLE test_case_node_versions (
    version_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '版本ID',
    node_id BIGINT NOT NULL COMMENT '对应节点ID',
    version_no INT NOT NULL COMMENT '版本号',
    operation_type VARCHAR(30) NOT NULL DEFAULT 'update' COMMENT '操作类型：create/update/rollback',
    change_note VARCHAR(500) DEFAULT NULL COMMENT '修改说明',
    title VARCHAR(300) NOT NULL COMMENT '版本标题',
    node_type VARCHAR(30) NOT NULL COMMENT '版本节点类型',
    precondition TEXT DEFAULT NULL COMMENT '版本前置条件',
    test_steps TEXT DEFAULT NULL COMMENT '版本测试步骤',
    expected_result TEXT DEFAULT NULL COMMENT '版本预期结果',
    priority VARCHAR(20) NOT NULL DEFAULT 'P1' COMMENT '版本优先级',
    snapshot_json JSON DEFAULT NULL COMMENT '完整快照JSON',
    rollback_from_version_id BIGINT DEFAULT NULL COMMENT '回退来源版本ID',
    created_by BIGINT NOT NULL COMMENT '版本创建人ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_case_node_versions_node FOREIGN KEY (node_id) REFERENCES test_case_nodes(node_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_node_versions_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_case_node_versions_rollback_from FOREIGN KEY (rollback_from_version_id) REFERENCES test_case_node_versions(version_id) ON DELETE SET NULL,
    UNIQUE KEY uk_case_node_versions_node_version (node_id, version_no),
    INDEX idx_case_node_versions_node_id (node_id),
    INDEX idx_case_node_versions_operation_type (operation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用例节点历史版本表';

CREATE TABLE test_tasks (
    task_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '测试任务ID',
    parent_id BIGINT DEFAULT NULL COMMENT '父任务ID（目录），子任务指向目录',
    task_name VARCHAR(200) NOT NULL COMMENT '任务名称',
    owner_id BIGINT DEFAULT NULL COMMENT '负责人ID',
    description TEXT DEFAULT NULL COMMENT '任务说明',
    status VARCHAR(30) NOT NULL DEFAULT 'draft' COMMENT '任务状态：draft/assigned/running/finished/cancelled',
    start_time DATETIME DEFAULT NULL COMMENT '计划开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '计划结束时间',
    created_by BIGINT NOT NULL COMMENT '创建人ID',
    updated_by BIGINT DEFAULT NULL COMMENT '更新人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_test_tasks_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_test_tasks_updated_by FOREIGN KEY (updated_by) REFERENCES users(user_id),
    CONSTRAINT fk_test_tasks_parent FOREIGN KEY (parent_id) REFERENCES test_tasks(task_id) ON DELETE SET NULL,
    CONSTRAINT fk_test_tasks_owner FOREIGN KEY (owner_id) REFERENCES users(user_id),
    INDEX idx_test_tasks_status (status),
    INDEX idx_test_tasks_is_deleted (is_deleted),
    INDEX idx_test_tasks_created_by (created_by),
    INDEX idx_test_tasks_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试任务表';

CREATE TABLE test_task_case_sets (
    task_case_set_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务用例集关联ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    case_set_id BIGINT NOT NULL COMMENT '用例集ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_task_case_sets_task FOREIGN KEY (task_id) REFERENCES test_tasks(task_id) ON DELETE CASCADE,
    CONSTRAINT fk_task_case_sets_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE CASCADE,
    UNIQUE KEY uk_task_case_sets_task_case_set (task_id, case_set_id),
    INDEX idx_task_case_sets_task_id (task_id),
    INDEX idx_task_case_sets_case_set_id (case_set_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试任务与用例集关联表';

CREATE TABLE test_task_assignees (
    task_assignee_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务执行人关联ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    assignee_id BIGINT NOT NULL COMMENT '执行人用户ID',
    assign_status VARCHAR(30) NOT NULL DEFAULT 'assigned' COMMENT '分配状态：assigned/accepted/finished',
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
    CONSTRAINT fk_task_assignees_task FOREIGN KEY (task_id) REFERENCES test_tasks(task_id) ON DELETE CASCADE,
    CONSTRAINT fk_task_assignees_user FOREIGN KEY (assignee_id) REFERENCES users(user_id),
    UNIQUE KEY uk_task_assignees_task_user (task_id, assignee_id),
    INDEX idx_task_assignees_task_id (task_id),
    INDEX idx_task_assignees_user_id (assignee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试任务执行人表';

CREATE TABLE test_execution_records (
    execution_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '执行记录ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    case_node_id BIGINT NOT NULL COMMENT '用例节点ID',
    executor_id BIGINT NOT NULL COMMENT '执行人ID',
    execution_status VARCHAR(30) NOT NULL DEFAULT 'not_run' COMMENT '执行状态：not_run/passed/failed/blocked/skipped',
    actual_result TEXT DEFAULT NULL COMMENT '实际结果',
    bug_description TEXT DEFAULT NULL COMMENT '缺陷描述',
    case_node_snapshot JSON DEFAULT NULL COMMENT '任务下发时的用例节点内容快照，避免后续编辑影响执行',
    sync_status VARCHAR(30) NOT NULL DEFAULT 'synced' COMMENT '同步状态：local_pending/synced/conflict',
    sync_version INT NOT NULL DEFAULT 1 COMMENT '同步版本号，用于冲突判断',
    executed_at DATETIME DEFAULT NULL COMMENT '执行时间',
    synced_at DATETIME DEFAULT NULL COMMENT '同步时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_execution_records_task FOREIGN KEY (task_id) REFERENCES test_tasks(task_id) ON DELETE CASCADE,
    CONSTRAINT fk_execution_records_case_node FOREIGN KEY (case_node_id) REFERENCES test_case_nodes(node_id) ON DELETE CASCADE,
    CONSTRAINT fk_execution_records_executor FOREIGN KEY (executor_id) REFERENCES users(user_id),
    UNIQUE KEY uk_execution_task_case_executor (task_id, case_node_id, executor_id),
    INDEX idx_execution_records_task_id (task_id),
    INDEX idx_execution_records_case_node_id (case_node_id),
    INDEX idx_execution_records_executor_id (executor_id),
    INDEX idx_execution_records_status (execution_status),
    INDEX idx_execution_records_sync_status (sync_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试执行记录表';

CREATE TABLE knowledge_bases (
    knowledge_base_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '知识库ID',
    name VARCHAR(200) NOT NULL COMMENT '知识库名称',
    description TEXT DEFAULT NULL COMMENT '知识库说明',
    product_type VARCHAR(100) DEFAULT NULL COMMENT '产品类型，例如camera/recorder/audio',
    hardware_module VARCHAR(100) DEFAULT NULL COMMENT '硬件模块，例如sensor/network/power',
    status VARCHAR(30) NOT NULL DEFAULT 'active' COMMENT '状态：active/disabled',
    created_by BIGINT NOT NULL COMMENT '创建人ID',
    updated_by BIGINT DEFAULT NULL COMMENT '更新人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_knowledge_bases_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_knowledge_bases_updated_by FOREIGN KEY (updated_by) REFERENCES users(user_id),
    INDEX idx_knowledge_bases_product_type (product_type),
    INDEX idx_knowledge_bases_hardware_module (hardware_module),
    INDEX idx_knowledge_bases_status (status),
    INDEX idx_knowledge_bases_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG知识库表';

CREATE TABLE faiss_indexes (
    faiss_index_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'FAISS索引ID',
    knowledge_base_id BIGINT NOT NULL COMMENT '所属知识库ID',
    index_name VARCHAR(100) NOT NULL COMMENT '索引名称',
    index_dir VARCHAR(500) NOT NULL COMMENT 'FAISS索引目录',
    index_file_path VARCHAR(500) DEFAULT NULL COMMENT 'FAISS索引文件路径',
    docstore_file_path VARCHAR(500) DEFAULT NULL COMMENT 'LangChain文档存储文件路径',
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'bge-small-zh' COMMENT 'Embedding模型名称',
    vector_dimension INT NOT NULL DEFAULT 512 COMMENT '向量维度，当前bge-small-zh-v1.5实测为512维',
    chunk_count INT NOT NULL DEFAULT 0 COMMENT '切片数量',
    vector_count INT NOT NULL DEFAULT 0 COMMENT '向量数量',
    status VARCHAR(30) NOT NULL DEFAULT 'active' COMMENT '状态：active/rebuilding/disabled',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_faiss_indexes_knowledge_base FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(knowledge_base_id) ON DELETE CASCADE,
    UNIQUE KEY uk_faiss_indexes_kb_name (knowledge_base_id, index_name),
    INDEX idx_faiss_indexes_knowledge_base_id (knowledge_base_id),
    INDEX idx_faiss_indexes_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='FAISS向量索引表';

CREATE TABLE knowledge_sources (
    source_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '知识来源ID',
    knowledge_base_id BIGINT NOT NULL COMMENT '所属知识库ID',
    source_name VARCHAR(255) NOT NULL COMMENT '知识来源名称',
    source_type VARCHAR(50) NOT NULL COMMENT '来源类型：xmind_case/hardware_spec/history_doc/manual_text',
    file_name VARCHAR(255) DEFAULT NULL COMMENT '文件名',
    file_path VARCHAR(500) DEFAULT NULL COMMENT '本地文件路径',
    storage_type VARCHAR(30) NOT NULL DEFAULT 'local' COMMENT '存储类型：local/object_storage',
    storage_key VARCHAR(500) DEFAULT NULL COMMENT '对象存储Key，预留云端扩展',
    content_text LONGTEXT DEFAULT NULL COMMENT '抽取后的完整文本',
    case_set_id BIGINT DEFAULT NULL COMMENT '关联用例集ID',
    status VARCHAR(30) NOT NULL DEFAULT 'active' COMMENT '状态：active/disabled',
    created_by BIGINT NOT NULL COMMENT '上传人ID',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_knowledge_sources_knowledge_base FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(knowledge_base_id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_sources_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE SET NULL,
    CONSTRAINT fk_knowledge_sources_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    INDEX idx_knowledge_sources_knowledge_base_id (knowledge_base_id),
    INDEX idx_knowledge_sources_source_type (source_type),
    INDEX idx_knowledge_sources_status (status),
    INDEX idx_knowledge_sources_case_set_id (case_set_id),
    INDEX idx_knowledge_sources_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG知识来源表';

CREATE TABLE knowledge_chunks (
    chunk_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '知识切片ID',
    chunk_uuid CHAR(36) NOT NULL UNIQUE COMMENT '稳定切片UUID',
    source_id BIGINT NOT NULL COMMENT '知识来源ID',
    faiss_index_id BIGINT NOT NULL COMMENT '所属FAISS索引ID',
    chunk_no INT NOT NULL COMMENT '切片序号',
    chunk_text TEXT NOT NULL COMMENT '切片文本',
    chunk_hash CHAR(64) DEFAULT NULL COMMENT '切片文本哈希，用于判断重复',
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'bge-small-zh' COMMENT 'Embedding模型名称',
    faiss_doc_id VARCHAR(100) NOT NULL COMMENT 'FAISS稳定文档ID，建议等于chunk_uuid',
    metadata_json JSON DEFAULT NULL COMMENT '切片元数据',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否逻辑删除',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_knowledge_chunks_source FOREIGN KEY (source_id) REFERENCES knowledge_sources(source_id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_chunks_faiss_index FOREIGN KEY (faiss_index_id) REFERENCES faiss_indexes(faiss_index_id) ON DELETE CASCADE,
    UNIQUE KEY uk_knowledge_chunks_faiss_doc (faiss_index_id, faiss_doc_id),
    INDEX idx_knowledge_chunks_source_id (source_id),
    INDEX idx_knowledge_chunks_faiss_index_id (faiss_index_id),
    INDEX idx_knowledge_chunks_faiss_source (faiss_index_id, source_id),
    INDEX idx_knowledge_chunks_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG知识切片表';

CREATE TABLE rag_retrieval_records (
    retrieval_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'RAG检索记录ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    knowledge_base_id BIGINT NOT NULL COMMENT '知识库ID',
    faiss_index_id BIGINT NOT NULL COMMENT 'FAISS索引ID',
    query_text TEXT NOT NULL COMMENT '用户检索需求',
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'bge-small-zh' COMMENT '查询向量模型',
    top_k INT NOT NULL DEFAULT 5 COMMENT '返回数量',
    retrieved_chunk_ids JSON DEFAULT NULL COMMENT '命中的chunk_id列表',
    retrieved_scores JSON DEFAULT NULL COMMENT '相似度分数列表',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_retrieval_records_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_retrieval_records_knowledge_base FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(knowledge_base_id),
    CONSTRAINT fk_retrieval_records_faiss_index FOREIGN KEY (faiss_index_id) REFERENCES faiss_indexes(faiss_index_id),
    INDEX idx_retrieval_records_user_id (user_id),
    INDEX idx_retrieval_records_knowledge_base_id (knowledge_base_id),
    INDEX idx_retrieval_records_faiss_index_id (faiss_index_id),
    INDEX idx_retrieval_records_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG检索记录表';

CREATE TABLE ai_generation_records (
    generation_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'AI生成记录ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    retrieval_id BIGINT DEFAULT NULL COMMENT '关联RAG检索记录ID',
    requirement_text TEXT NOT NULL COMMENT '用户测试需求',
    model_provider VARCHAR(50) NOT NULL DEFAULT 'DeepSeek' COMMENT '模型服务商',
    model_name VARCHAR(100) NOT NULL DEFAULT 'deepseek-v4-flash' COMMENT '模型名称',
    prompt_template_version VARCHAR(50) DEFAULT NULL COMMENT '提示词模板版本',
    prompt_variables_json JSON DEFAULT NULL COMMENT '提示词变量，不重复存储大段上下文',
    used_chunk_ids JSON DEFAULT NULL COMMENT '生成时使用的chunk_id列表',
    generated_text LONGTEXT NOT NULL COMMENT 'AI生成的原始结果',
    generated_json JSON DEFAULT NULL COMMENT '结构化生成结果',
    case_set_id BIGINT DEFAULT NULL COMMENT '生成后保存的用例集ID',
    generation_status VARCHAR(30) NOT NULL DEFAULT 'success' COMMENT '生成状态：success/failed',
    error_message TEXT DEFAULT NULL COMMENT '失败原因',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_ai_generation_records_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_ai_generation_records_retrieval FOREIGN KEY (retrieval_id) REFERENCES rag_retrieval_records(retrieval_id) ON DELETE SET NULL,
    CONSTRAINT fk_ai_generation_records_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE SET NULL,
    INDEX idx_ai_generation_records_user_id (user_id),
    INDEX idx_ai_generation_records_retrieval_id (retrieval_id),
    INDEX idx_ai_generation_records_case_set_id (case_set_id),
    INDEX idx_ai_generation_records_status (generation_status),
    INDEX idx_ai_generation_records_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI测试用例生成记录表';

CREATE TABLE case_node_metas (
    meta_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '节点元数据ID',
    case_set_id BIGINT NOT NULL COMMENT '所属用例集ID',
    node_id BIGINT NOT NULL COMMENT '节点ID',
    meta_type VARCHAR(30) NOT NULL COMMENT '元数据类型：tag/note/link/image/review',
    meta_key VARCHAR(50) DEFAULT NULL COMMENT '类型内键名，如tag文本',
    meta_value JSON DEFAULT NULL COMMENT '元数据内容JSON',
    created_by BIGINT DEFAULT NULL COMMENT '创建人ID',
    updated_by BIGINT DEFAULT NULL COMMENT '更新人ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_case_node_metas_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_node_metas_node FOREIGN KEY (node_id) REFERENCES test_case_nodes(node_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_node_metas_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    CONSTRAINT fk_case_node_metas_updated_by FOREIGN KEY (updated_by) REFERENCES users(user_id),
    UNIQUE KEY uk_case_node_metas (case_set_id, node_id, meta_type, meta_key),
    INDEX idx_case_node_metas_case_set (case_set_id),
    INDEX idx_case_node_metas_node (node_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用例节点脑图元数据表（标签/备注/链接/图片/评审）';

CREATE TABLE case_set_snapshots (
    snapshot_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '脑图快照ID',
    case_set_id BIGINT NOT NULL COMMENT '所属用例集ID',
    name VARCHAR(200) NOT NULL COMMENT '快照名称',
    data_json JSON NOT NULL COMMENT '快照数据（标签/备注/链接/图片/评审/折叠/外观）',
    created_by BIGINT NOT NULL COMMENT '创建人ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_case_set_snapshots_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_set_snapshots_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    INDEX idx_case_set_snapshots_case_set (case_set_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用例集脑图版本快照表';

CREATE TABLE case_set_reviews (
    review_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用例集评审记录ID',
    case_set_id BIGINT NOT NULL COMMENT '所属用例集ID',
    reviewer_ids JSON NOT NULL COMMENT '评审人ID列表',
    due_at DATETIME DEFAULT NULL COMMENT '截止时间',
    note TEXT DEFAULT NULL COMMENT '评审说明',
    status VARCHAR(30) NOT NULL DEFAULT 'submitted' COMMENT '评审状态：submitted/reviewing/completed',
    conclusion TEXT DEFAULT NULL COMMENT '评审结论（完成后填写）',
    created_by BIGINT NOT NULL COMMENT '发起人ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT fk_case_set_reviews_case_set FOREIGN KEY (case_set_id) REFERENCES test_case_sets(case_set_id) ON DELETE CASCADE,
    CONSTRAINT fk_case_set_reviews_created_by FOREIGN KEY (created_by) REFERENCES users(user_id),
    INDEX idx_case_set_reviews_case_set (case_set_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用例集评审记录表';
