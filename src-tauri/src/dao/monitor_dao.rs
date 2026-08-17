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
        r#"
            WITH ranked AS (
                SELECT id,account_id,account_name,account_type,model,checked_at,duration_ms,success,status_code,error_code,error_message,
                       ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY checked_at DESC,id DESC) AS row_number
                FROM monitor_records
                WHERE account_id IN ({})
            )
            SELECT id,account_id,account_name,account_type,model,checked_at,duration_ms,success,status_code,error_code,error_message
            FROM ranked
            WHERE row_number <= ?
            ORDER BY account_id,checked_at DESC,id DESC
        "#,
        placeholders
    );
    let mut query = sqlx::query_as::<_, MonitorRecord>(&q);
    for id in ids {
        query = query.bind(id);
    }
    Ok(query.bind(limit.max(1)).fetch_all(pool).await?)
}
pub async fn create(pool: &SqlitePool, r: &MonitorRecord) -> Result<(), AppError> {
    sqlx::query("INSERT INTO monitor_records(id,account_id,account_name,account_type,model,checked_at,duration_ms,success,status_code,error_code,error_message) VALUES(?,?,?,?,?,?,?,?,?,?,?)").bind(&r.id).bind(&r.account_id).bind(&r.account_name).bind(&r.account_type).bind(&r.model).bind(&r.checked_at).bind(r.duration_ms).bind(r.success).bind(r.status_code).bind(&r.error_code).bind(&r.error_message).execute(pool).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{create, list_grouped};
    use crate::{database::connect, model::monitor_record::MonitorRecord};

    fn record(account_id: &str, second: u8) -> MonitorRecord {
        MonitorRecord {
            id: uuid::Uuid::new_v4().to_string(),
            account_id: account_id.to_owned(),
            account_name: account_id.to_owned(),
            account_type: "openai".to_owned(),
            model: Some("gpt-5.6".to_owned()),
            checked_at: format!("2026-08-17T00:00:{second:02}Z"),
            duration_ms: Some(100),
            success: true,
            status_code: Some(200),
            error_code: None,
            error_message: None,
        }
    }

    #[tokio::test]
    async fn returns_the_latest_limit_for_each_account() {
        let path = std::env::temp_dir().join(format!(
            "aimux-monitor-records-{}.sqlite3",
            uuid::Uuid::new_v4()
        ));
        let pool = connect(&path).await.expect("创建数据库失败");
        for account_id in ["account-a", "account-b"] {
            for second in 1..=3 {
                create(&pool, &record(account_id, second))
                    .await
                    .expect("写入监控记录失败");
            }
        }
        let ids = vec!["account-a".to_owned(), "account-b".to_owned()];
        let records = list_grouped(&pool, &ids, 2)
            .await
            .expect("读取监控记录失败");
        assert_eq!(records.len(), 4);
        for account_id in &ids {
            let account_records = records
                .iter()
                .filter(|record| record.account_id == *account_id)
                .collect::<Vec<_>>();
            assert_eq!(account_records.len(), 2);
            assert!(account_records
                .iter()
                .all(|record| record.checked_at.ends_with("02Z")
                    || record.checked_at.ends_with("03Z")));
        }
        pool.close().await;
        let _ = std::fs::remove_file(path);
    }
}
