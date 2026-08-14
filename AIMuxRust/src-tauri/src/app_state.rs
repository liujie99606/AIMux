use std::sync::Arc;

use sqlx::SqlitePool;

use crate::{
    config::{Settings, SharedSettings},
    database,
    error::AppError,
};

pub struct AppState {
    pub pool: SqlitePool,
    pub settings: SharedSettings,
}

impl AppState {
    pub async fn initialize(settings: Settings) -> Result<Self, AppError> {
        let pool = database::connect(&settings.database_path()).await?;
        crate::service::model_service::seed(&pool).await?;
        Ok(Self {
            pool,
            settings: Arc::new(tokio::sync::RwLock::new(settings)),
        })
    }
}
