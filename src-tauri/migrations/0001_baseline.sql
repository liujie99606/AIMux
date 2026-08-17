CREATE TABLE accounts (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL,
    multiplier NUMERIC(4, 2) NOT NULL,
    supported_models TEXT,
    tags TEXT,
    notes TEXT,
    last_error_code TEXT,
    last_error_message TEXT,
    last_successful_test_model TEXT,
    last_used_at TEXT,
    total_requests INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    test_default_model TEXT,
    model_mappings TEXT,
    CONSTRAINT ck_accounts_type CHECK (type IN ('openai', 'anthropic')),
    CONSTRAINT ck_accounts_status CHECK (status IN ('active', 'disabled')),
    CONSTRAINT ck_accounts_priority CHECK (priority BETWEEN 0 AND 9),
    CONSTRAINT ck_accounts_multiplier CHECK (multiplier BETWEEN 0.01 AND 0.30)
);
CREATE INDEX idx_accounts_dispatch ON accounts(status, priority, id);
CREATE INDEX ix_accounts_priority ON accounts(priority);
CREATE INDEX ix_accounts_status ON accounts(status);
CREATE INDEX ix_accounts_type ON accounts(type);

CREATE TABLE models (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    is_default INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT ck_models_type CHECK (type IN ('openai', 'anthropic')),
    CONSTRAINT uq_models_type_name UNIQUE (type, name)
);
CREATE INDEX idx_models_type_name ON models(type, name);
CREATE INDEX ix_models_name ON models(name);
CREATE INDEX ix_models_type ON models(type);

CREATE TABLE usage_records (
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
    stream BOOLEAN NOT NULL,
    success BOOLEAN NOT NULL,
    status_code INTEGER,
    error_code TEXT,
    error_message TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cached_tokens INTEGER,
    client_ip TEXT,
    attempts INTEGER NOT NULL
);
CREATE INDEX idx_usage_started ON usage_records(started_at, id);
CREATE INDEX idx_usage_account ON usage_records(account_id, started_at);
CREATE INDEX idx_usage_model ON usage_records(model, started_at);
CREATE INDEX ix_usage_records_account_id ON usage_records(account_id);
CREATE INDEX ix_usage_records_model ON usage_records(model);
CREATE INDEX ix_usage_records_started_at ON usage_records(started_at);
CREATE INDEX ix_usage_records_trace_id ON usage_records(trace_id);

CREATE TABLE monitor_records (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    model TEXT,
    checked_at TEXT NOT NULL,
    duration_ms INTEGER,
    success BOOLEAN NOT NULL,
    status_code INTEGER,
    error_code TEXT,
    error_message TEXT
);
CREATE INDEX idx_monitor_account_checked ON monitor_records(account_id, checked_at);
CREATE INDEX idx_monitor_checked ON monitor_records(checked_at, id);
CREATE INDEX ix_monitor_records_account_id ON monitor_records(account_id);
CREATE INDEX ix_monitor_records_checked_at ON monitor_records(checked_at);
