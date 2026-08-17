use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct Paged<T> {
    pub items: Vec<T>,
    pub total: i64,
}

#[derive(Debug, Serialize)]
pub struct ErrorBody {
    pub detail: String,
}

#[derive(Debug, Deserialize)]
pub struct OffsetLimit {
    #[serde(default)]
    pub offset: i64,
    #[serde(default = "default_limit")]
    pub limit: i64,
}
fn default_limit() -> i64 {
    20
}
