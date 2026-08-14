use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct UsageRecord {
    pub id: String,
    pub trace_id: String,
    pub started_at: String,
    pub ended_at: Option<String>,
    pub duration_ms: Option<i64>,
    pub first_token_ms: Option<i64>,
    pub account_id: Option<String>,
    pub account_name: Option<String>,
    pub account_type: Option<String>,
    pub model: Option<String>,
    pub reasoning_effort: Option<String>,
    pub endpoint: Option<String>,
    pub stream: bool,
    pub success: bool,
    pub status_code: Option<i64>,
    pub error_code: Option<String>,
    pub error_message: Option<String>,
    pub input_tokens: Option<i64>,
    pub output_tokens: Option<i64>,
    pub total_tokens: Option<i64>,
    pub cached_tokens: Option<i64>,
    pub client_ip: Option<String>,
    pub attempts: i64,
}
