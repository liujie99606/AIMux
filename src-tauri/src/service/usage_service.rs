use crate::{
    dao::usage_dao,
    error::AppError,
    model::usage_record::UsageRecord,
    schema::usage_schema::{UsageResponse, UsageSummary},
};
use chrono::{Duration, Utc};
use sqlx::SqlitePool;

pub async fn list(
    pool: &SqlitePool,
    offset: i64,
    limit: i64,
    account_id: Option<&str>,
    model: Option<&str>,
    kind: Option<&str>,
    success: Option<bool>,
    started_after: Option<&str>,
    started_before: Option<&str>,
) -> Result<UsageResponse<UsageRecord>, AppError> {
    let (items, total) = usage_dao::list(
        pool,
        offset.max(0),
        limit.clamp(1, 200),
        account_id,
        model,
        kind,
        success,
        started_after,
        started_before,
    )
    .await?;
    let summary = summary(
        pool,
        account_id,
        model,
        kind,
        success,
        started_after,
        started_before,
    )
    .await?;
    Ok(UsageResponse {
        items,
        total,
        summary,
    })
}
async fn summary(
    pool: &SqlitePool,
    account_id: Option<&str>,
    model: Option<&str>,
    kind: Option<&str>,
    success: Option<bool>,
    started_after: Option<&str>,
    started_before: Option<&str>,
) -> Result<UsageSummary, AppError> {
    let mut where_sql = String::from(" WHERE 1=1");
    let mut vals: Vec<String> = Vec::new();
    if let Some(v) = account_id {
        where_sql.push_str(" AND account_id=?");
        vals.push(v.into())
    }
    if let Some(v) = model {
        where_sql.push_str(" AND model=?");
        vals.push(v.into())
    }
    if let Some(v) = kind {
        where_sql.push_str(" AND account_type=?");
        vals.push(v.into())
    }
    if let Some(v) = success {
        where_sql.push_str(" AND success=?");
        vals.push((v as i32).to_string())
    }
    if let Some(v) = started_after {
        where_sql.push_str(" AND started_at>=?");
        vals.push(v.into())
    }
    if let Some(v) = started_before {
        where_sql.push_str(" AND started_at<=?");
        vals.push(v.into())
    }
    let q=format!("SELECT COUNT(*),COALESCE(SUM(success),0),COALESCE(AVG(duration_ms),0),COALESCE(SUM(total_tokens),0) FROM usage_records{}",where_sql);
    let mut query = sqlx::query_as::<_, (i64, i64, f64, i64)>(&q);
    for v in vals {
        query = query.bind(v);
    }
    let (count, ok, avg, tokens) = query.fetch_one(pool).await?;
    Ok(UsageSummary {
        request_count: count,
        success_rate: if count == 0 {
            0.0
        } else {
            ok as f64 / count as f64
        },
        average_duration_ms: avg.round() as i64,
        total_tokens: tokens,
    })
}
pub async fn detail(pool: &SqlitePool, id: &str) -> Result<Option<UsageRecord>, AppError> {
    usage_dao::get(pool, id).await
}
pub async fn cleanup(pool: &SqlitePool) -> Result<i64, AppError> {
    usage_dao::cleanup(
        pool,
        &(Utc::now() - Duration::days(3))
            .format("%Y-%m-%dT%H:%M:%SZ")
            .to_string(),
    )
    .await
}
