use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct MonitorRecord {
    pub id: String,
    pub account_id: String,
    pub account_name: String,
    pub account_type: String,
    pub model: Option<String>,
    pub checked_at: String,
    pub duration_ms: Option<i64>,
    pub success: bool,
    pub status_code: Option<i64>,
    pub error_code: Option<String>,
    pub error_message: Option<String>,
}
