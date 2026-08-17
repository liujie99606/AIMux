use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct UsageSummary {
    pub request_count: i64,
    pub success_rate: f64,
    pub average_duration_ms: i64,
    pub total_tokens: i64,
}
#[derive(Debug, Serialize)]
pub struct UsageResponse<T> {
    pub items: Vec<T>,
    pub total: i64,
    pub summary: UsageSummary,
}
#[derive(Debug, Serialize)]
pub struct TokenSummary {
    pub input_tokens: i64,
    pub output_tokens: i64,
    pub cached_tokens: i64,
    pub total_tokens: i64,
    pub cache_rate: Option<f64>,
}
