-- AIMux SQLite 初始建表脚本。
-- 正常启动会由 app/db.py 自动执行 SQLModel.metadata.create_all()；
-- 本脚本用于手动初始化空数据库或审阅当前表结构，不包含任何迁移或删除操作。

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'openai' CHECK (type IN ('openai', 'anthropic')),
  base_url TEXT NOT NULL,
  api_key_encrypted BLOB NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
  priority INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 0 AND 9),
  supported_models TEXT,
  tags TEXT,
  notes TEXT,
  last_error_code TEXT,
  last_error_message TEXT,
  last_successful_test_model TEXT,
  last_used_at TEXT,
  total_requests INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_dispatch
  ON accounts (status, priority, id);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts (type);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts (status);
CREATE INDEX IF NOT EXISTS idx_accounts_priority ON accounts (priority);

CREATE TABLE IF NOT EXISTS models (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('openai', 'anthropic')),
  is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CONSTRAINT uq_models_type_name UNIQUE (type, name)
);

CREATE INDEX IF NOT EXISTS idx_models_type_name ON models (type, name);

-- 默认模型仅在不存在时补充，应用启动也会执行同样的幂等初始化。
-- 每个协议类型的第一个模型标记为测试默认（is_default=1）。
INSERT OR IGNORE INTO models (id, name, type, is_default, created_at, updated_at) VALUES
  ('default-openai-gpt-5-5', 'gpt-5.5', 'openai', 1, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-openai-gpt-5-5-pro', 'gpt-5.5-pro', 'openai', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-openai-gpt-5-6', 'gpt-5.6', 'openai', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-openai-gpt-5-6-sol', 'gpt-5.6-sol', 'openai', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-openai-gpt-5-6-terra', 'gpt-5.6-terra', 'openai', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-openai-gpt-5-6-luna', 'gpt-5.6-luna', 'openai', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-anthropic-claude-opus-4-8', 'claude-opus-4-8', 'anthropic', 1, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-anthropic-claude-sonnet-4-8', 'claude-sonnet-4-8', 'anthropic', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  ('default-anthropic-claude-haiku-4-8', 'claude-haiku-4-8', 'anthropic', 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

CREATE TABLE IF NOT EXISTS usage_records (
  id TEXT PRIMARY KEY NOT NULL,
  trace_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  duration_ms INTEGER,
  first_token_ms INTEGER,
  account_id TEXT,
  account_name TEXT,
  account_type TEXT,
  model TEXT,
  reasoning_effort TEXT,
  endpoint TEXT,
  stream INTEGER NOT NULL DEFAULT 0,
  success INTEGER NOT NULL DEFAULT 0,
  status_code INTEGER,
  error_code TEXT,
  error_message TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  total_tokens INTEGER,
  client_ip TEXT,
  attempts INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_usage_started
  ON usage_records (started_at, id);
CREATE INDEX IF NOT EXISTS idx_usage_account
  ON usage_records (account_id, started_at);
CREATE INDEX IF NOT EXISTS idx_usage_model
  ON usage_records (model, started_at);
CREATE INDEX IF NOT EXISTS idx_usage_trace_id ON usage_records (trace_id);

COMMIT;
