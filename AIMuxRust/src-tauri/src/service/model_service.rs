use crate::{dao::model_dao, error::AppError, schema::model_schema::ModelView};
use sqlx::SqlitePool;

const DEFAULTS: [(&str, &str); 9] = [
    ("openai", "gpt-5.5"),
    ("openai", "gpt-5.5-pro"),
    ("openai", "gpt-5.6"),
    ("openai", "gpt-5.6-sol"),
    ("openai", "gpt-5.6-terra"),
    ("openai", concat!("gpt-5.6-", "luna")),
    ("anthropic", "claude-opus-4-8"),
    ("anthropic", "claude-sonnet-4-8"),
    ("anthropic", "claude-haiku-4-8"),
];

pub async fn seed(pool: &SqlitePool) -> Result<(), AppError> {
    for (kind, name) in DEFAULTS {
        if sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM models WHERE type=? AND name=?")
            .bind(kind)
            .bind(name)
            .fetch_one(pool)
            .await?
            == 0
        {
            let id = uuid::Uuid::new_v4().to_string();
            let now = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
            sqlx::query("INSERT INTO models(id,name,type,is_default,created_at,updated_at) VALUES(?,?,?,0,?,?)")
                .bind(id).bind(name).bind(kind).bind(&now).bind(&now).execute(pool).await?;
        }
    }
    model_dao::ensure_defaults(pool).await
}

pub async fn list(pool: &SqlitePool, kind: Option<&str>) -> Result<Vec<ModelView>, AppError> {
    Ok(model_dao::list(pool, kind)
        .await?
        .into_iter()
        .map(model_dao::to_view)
        .collect())
}
