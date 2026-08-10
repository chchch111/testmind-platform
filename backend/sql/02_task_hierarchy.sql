-- 任务父子层级与负责人迁移
-- 父任务（parent_id 为空）= 目录；子任务（parent_id 指向目录）= 执行单元
USE rag_mindmap_test_platform;

ALTER TABLE test_tasks
  ADD COLUMN parent_id BIGINT DEFAULT NULL COMMENT '父任务ID（目录），子任务指向目录' AFTER task_name,
  ADD COLUMN owner_id  BIGINT DEFAULT NULL COMMENT '负责人ID' AFTER parent_id;

ALTER TABLE test_tasks
  ADD CONSTRAINT fk_test_tasks_parent FOREIGN KEY (parent_id) REFERENCES test_tasks(task_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_test_tasks_owner  FOREIGN KEY (owner_id) REFERENCES users(user_id);

CREATE INDEX idx_test_tasks_parent_id ON test_tasks(parent_id);
