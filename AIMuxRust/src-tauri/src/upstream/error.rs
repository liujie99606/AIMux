use reqwest::StatusCode;

#[derive(Debug, Clone)]
pub struct UpstreamError {
    pub status: StatusCode,
    pub code: String,
    pub message: String,
}
