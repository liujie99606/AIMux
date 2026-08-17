use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct MonitorRecordView {
    pub checked_at: String,
    pub model: Option<String>,
    pub success: bool,
    pub duration_ms: Option<i64>,
    pub status_code: Option<i64>,
    pub error_code: Option<String>,
    pub error_message: Option<String>,
}
#[derive(Debug, Serialize)]
pub struct MonitorAccountView {
    pub account_id: String,
    pub account_name: String,
    #[serde(rename = "account_type")]
    pub account_type: String,
    pub multiplier: f64,
    pub model: Option<String>,
    pub records: Vec<MonitorRecordView>,
}
#[derive(Debug, Serialize)]
pub struct MonitorResponse {
    pub items: Vec<MonitorAccountView>,
    pub monitoring_enabled: bool,
}
