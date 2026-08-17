use crate::{app_state::AppState, error::AppError};
use axum::{extract::State, routing::get, Json, Router};
use std::sync::Arc;
pub fn routes() -> Router<Arc<AppState>> {
    Router::new().route("/api/settings", get(get_settings).put(update_settings))
}
async fn get_settings(State(s): State<Arc<AppState>>) -> Json<crate::config::Settings> {
    Json(s.settings.read().await.clone())
}
async fn update_settings(
    State(s): State<Arc<AppState>>,
    Json(value): Json<crate::config::Settings>,
) -> Result<Json<crate::config::Settings>, AppError> {
    value
        .save()
        .map_err(|e| AppError::Internal(e.to_string()))?;
    *s.settings.write().await = value.clone();
    Ok(Json(value))
}
