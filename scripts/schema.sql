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
