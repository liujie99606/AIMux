use crate::{error::AppError, model::monitor_record::MonitorRecord};
use sqlx::SqlitePool;

pub async fn list_grouped(
    pool: &SqlitePool,
    ids: &[String],
    limit: i64,
) -> Result<Vec<MonitorRecord>, AppError> {
    if ids.is_empty() {
        return Ok(Vec::new());
    }
    let placeholders = std::iter::repeat("?")
        .take(ids.len())
        .collect::<Vec<_>>()
        .join(",");
    let q = format!(
        "SELECT * FROM monitor_records WHERE account_id IN ({}) ORDER BY checked_at DESC,id DESC",
        placeholders
    );
    let mut query = sqlx::query_as::<_, MonitorRecord>(&q);
    for id in ids {
        query = query.bind(id);
    }
    let mut rows = query.fetch_all(pool).await?;
    rows.truncate((limit.max(1) * ids.len() as i64) as usize);
    Ok(rows)
}
pub async fn create(pool: &SqlitePool, r: &MonitorRecord) -> Result<(), AppError> {
    sqlx::query("INSERT INTO monitor_records(id,account_id,account_name,account_type,model,checked_at,duration_ms,success,status_code,error_code,error_message) VALUES(?,?,?,?,?,?,?,?,?,?,?)").bind(&r.id).bind(&r.account_id).bind(&r.account_name).bind(&r.account_type).bind(&r.model).bind(&r.checked_at).bind(r.duration_ms).bind(r.success).bind(r.status_code).bind(&r.error_code).bind(&r.error_message).execute(pool).await?;
    Ok(())
}
