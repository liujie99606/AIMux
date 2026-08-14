use crate::{app_state::AppState, error::AppError, service::statistics_service};
use axum::{extract::State, routing::get, Json, Router};
use std::sync::Arc;
pub fn routes() -> Router<Arc<AppState>> {
    Router::new().route("/api/usage/statistics", get(statistics))
}
async fn statistics(State(s): State<Arc<AppState>>) -> Result<Json<serde_json::Value>, AppError> {
    Ok(Json(statistics_service::tokens(&s.pool).await?))
}
