use sqlx::SqlitePool;
use uuid::Uuid;

use crate::{
    error::AppError,
    model::catalog_model::CatalogModel,
    schema::model_schema::{ModelCreate, ModelUpdate, ModelView},
};

pub async fn list(pool: &SqlitePool, kind: Option<&str>) -> Result<Vec<CatalogModel>, AppError> {
    let mut q = String::from("SELECT * FROM models");
    if kind.is_some() {
        q.push_str(" WHERE type=?");
    }
    q.push_str(" ORDER BY type, is_default DESC, lower(name), id");
    let mut query = sqlx::query_as::<_, CatalogModel>(&q);
    if let Some(k) = kind {
        query = query.bind(k);
    }
    Ok(query.fetch_all(pool).await?)
}
pub async fn get(pool: &SqlitePool, id: &str) -> Result<Option<CatalogModel>, AppError> {
    Ok(
        sqlx::query_as::<_, CatalogModel>("SELECT * FROM models WHERE id=?")
            .bind(id)
            .fetch_optional(pool)
            .await?,
    )
}
pub async fn default_name(pool: &SqlitePool, kind: &str) -> Result<Option<String>, AppError> {
    Ok(
        sqlx::query_scalar("SELECT name FROM models WHERE type=? AND is_default=1 LIMIT 1")
            .bind(kind)
            .fetch_optional(pool)
            .await?,
    )
}
pub async fn insert_missing(pool: &SqlitePool, defaults: &[(&str, &str)]) -> Result<(), AppError> {
    let now = now();
    for (kind, name) in defaults {
        sqlx::query("INSERT OR IGNORE INTO models(id,name,type,is_default,created_at,updated_at) VALUES(?,?,?,0,?,?)")
            .bind(Uuid::new_v4().to_string())
            .bind(name)
            .bind(kind)
            .bind(&now)
            .bind(&now)
            .execute(pool)
            .await?;
    }
    Ok(())
}
pub async fn create(pool: &SqlitePool, p: ModelCreate) -> Result<CatalogModel, AppError> {
    if !["openai", "anthropic"].contains(&p.model_type.as_str()) {
        return Err(AppError::BadRequest("协议类型不支持".into()));
    }
    if sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM models WHERE type=? AND name=?")
        .bind(&p.model_type)
        .bind(p.name.trim())
        .fetch_one(pool)
        .await?
        > 0
    {
        return Err(AppError::BadRequest("该类型下的模型名称已存在".into()));
    }
    let id = Uuid::new_v4().to_string();
    let now = now();
    sqlx::query(
        "INSERT INTO models(id,name,type,is_default,created_at,updated_at) VALUES(?,?,?,0,?,?)",
    )
    .bind(&id)
    .bind(p.name.trim())
    .bind(p.model_type)
    .bind(&now)
    .bind(&now)
    .execute(pool)
    .await?;
    get(pool, &id)
        .await?
        .ok_or_else(|| AppError::Internal("创建模型后读取失败".into()))
}
pub async fn update(
    pool: &SqlitePool,
    current: CatalogModel,
    p: ModelUpdate,
) -> Result<CatalogModel, AppError> {
    let name = p.name.unwrap_or(current.name.clone());
    let kind = p.model_type.unwrap_or(current.r#type.clone());
    if sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM models WHERE type=? AND name=? AND id<>?")
        .bind(&kind)
        .bind(&name)
        .bind(&current.id)
        .fetch_one(pool)
        .await?
        > 0
    {
        return Err(AppError::BadRequest("该类型下的模型名称已存在".into()));
    }
    let is_default = if kind != current.r#type {
        0
    } else {
        current.is_default
    };
    sqlx::query("UPDATE models SET name=?,type=?,is_default=?,updated_at=? WHERE id=?")
        .bind(name)
        .bind(kind)
        .bind(is_default)
        .bind(now())
        .bind(&current.id)
        .execute(pool)
        .await?;
    get(pool, &current.id)
        .await?
        .ok_or_else(|| AppError::Internal("更新模型后读取失败".into()))
}
pub async fn delete(pool: &SqlitePool, id: &str) -> Result<(), AppError> {
    sqlx::query("DELETE FROM models WHERE id=?")
        .bind(id)
        .execute(pool)
        .await?;
    ensure_defaults(pool).await
}
pub async fn set_default(
    pool: &SqlitePool,
    current: CatalogModel,
) -> Result<CatalogModel, AppError> {
    let mut transaction = pool.begin().await?;
    sqlx::query("UPDATE models SET is_default=0,updated_at=? WHERE type=?")
        .bind(now())
        .bind(&current.r#type)
        .execute(&mut *transaction)
        .await?;
    sqlx::query("UPDATE models SET is_default=1,updated_at=? WHERE id=?")
        .bind(now())
        .bind(&current.id)
        .execute(&mut *transaction)
        .await?;
    transaction.commit().await?;
    get(pool, &current.id)
        .await?
        .ok_or_else(|| AppError::Internal("设置默认模型后读取失败".into()))
}
pub async fn ensure_defaults(pool: &SqlitePool) -> Result<(), AppError> {
    for kind in ["openai", "anthropic"] {
        let exists = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM models WHERE type=? AND is_default=1",
        )
        .bind(kind)
        .fetch_one(pool)
        .await?;
        if exists == 0 {
            if let Some(item) = sqlx::query_as::<_, CatalogModel>(
                "SELECT * FROM models WHERE type=? ORDER BY lower(name),id LIMIT 1",
            )
            .bind(kind)
            .fetch_optional(pool)
            .await?
            {
                sqlx::query("UPDATE models SET is_default=1,updated_at=? WHERE id=?")
                    .bind(now())
                    .bind(item.id)
                    .execute(pool)
                    .await?;
            }
        }
    }
    Ok(())
}
pub fn to_view(m: CatalogModel) -> ModelView {
    ModelView {
        id: m.id,
        name: m.name,
        model_type: m.r#type,
        is_default: m.is_default,
        created_at: m.created_at,
        updated_at: m.updated_at,
    }
}
fn now() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

#[cfg(test)]
mod tests {
    use super::{create, get, set_default};
    use crate::{database::connect, schema::model_schema::ModelCreate};

    #[tokio::test]
    async fn switches_the_only_default_model_in_a_transaction() {
        let path = std::env::temp_dir().join(format!(
            "aimux-model-default-{}.sqlite3",
            uuid::Uuid::new_v4()
        ));
        let pool = connect(&path).await.expect("创建数据库失败");
        let first = create(
            &pool,
            ModelCreate {
                name: "model-a".into(),
                model_type: "openai".into(),
            },
        )
        .await
        .expect("创建第一个模型失败");
        let second = create(
            &pool,
            ModelCreate {
                name: "model-b".into(),
                model_type: "openai".into(),
            },
        )
        .await
        .expect("创建第二个模型失败");
        set_default(&pool, first)
            .await
            .expect("设置第一个默认模型失败");
        let duplicate_default = sqlx::query("UPDATE models SET is_default=1 WHERE id=?")
            .bind(&second.id)
            .execute(&pool)
            .await;
        assert!(duplicate_default.is_err());
        set_default(&pool, second.clone())
            .await
            .expect("切换默认模型失败");
        let defaults: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM models WHERE type='openai' AND is_default=1")
                .fetch_one(&pool)
                .await
                .expect("读取默认模型数量失败");
        assert_eq!(defaults, 1);
        assert_eq!(
            get(&pool, &second.id)
                .await
                .expect("读取第二个模型失败")
                .expect("第二个模型不存在")
                .is_default,
            1
        );
        pool.close().await;
        let _ = std::fs::remove_file(path);
    }
}
