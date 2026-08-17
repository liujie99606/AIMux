use crate::{
    dao::{account_dao, usage_dao},
    error::AppError,
    schema::usage_schema::TokenSummary,
};
use chrono::{Duration, Local, TimeZone, Utc};
use sqlx::SqlitePool;
use std::collections::HashMap;

pub async fn tokens(pool: &SqlitePool) -> Result<serde_json::Value, AppError> {
    let today = Local::now().date_naive();
    let start_today = Local
        .from_local_datetime(&today.and_hms_opt(0, 0, 0).unwrap())
        .single()
        .unwrap()
        .with_timezone(&Utc);
    let start_yesterday = start_today - Duration::days(1);
    let total = range(pool, None, None).await?;
    let yesterday = range(pool, Some(start_yesterday), Some(start_today)).await?;
    let today_summary = range(
        pool,
        Some(start_today),
        Some(start_today + Duration::days(1)),
    )
    .await?;
    let (accounts, _) = account_dao::list(pool, 0, 10000, None, Some("active")).await?;
    let mut account_summaries =
        range_for_accounts(pool, start_today, start_today + Duration::days(1)).await?;
    let mut account_today = Vec::new();
    for account in accounts {
        let s = account_summaries
            .remove(&account.id)
            .unwrap_or_else(|| summary(0, 0, 0, 0));
        account_today.push(serde_json::json!({"account_id":account.id,"account_name":account.name,"account_type":account.r#type,"priority":account.priority,"input_tokens":s.input_tokens,"output_tokens":s.output_tokens,"cached_tokens":s.cached_tokens,"total_tokens":s.total_tokens,"cache_rate":s.cache_rate}));
    }
    Ok(
        serde_json::json!({"total":total,"yesterday":yesterday,"today":today_summary,"accounts_today":account_today}),
    )
}
async fn range(
    pool: &SqlitePool,
    start: Option<chrono::DateTime<Utc>>,
    end: Option<chrono::DateTime<Utc>>,
) -> Result<TokenSummary, AppError> {
    let start = start.map(|value| value.format("%Y-%m-%dT%H:%M:%SZ").to_string());
    let end = end.map(|value| value.format("%Y-%m-%dT%H:%M:%SZ").to_string());
    let (a, b, c, d) = usage_dao::token_totals(pool, start.as_deref(), end.as_deref()).await?;
    Ok(summary(a, b, c, d))
}
async fn range_for_accounts(
    pool: &SqlitePool,
    start: chrono::DateTime<Utc>,
    end: chrono::DateTime<Utc>,
) -> Result<HashMap<String, TokenSummary>, AppError> {
    let start = start.format("%Y-%m-%dT%H:%M:%SZ").to_string();
    let end = end.format("%Y-%m-%dT%H:%M:%SZ").to_string();
    let rows = usage_dao::token_totals_by_account(pool, &start, &end).await?;
    Ok(rows
        .into_iter()
        .map(|(account_id, input, output, cached, total)| {
            (account_id, summary(input, output, cached, total))
        })
        .collect())
}
fn summary(a: i64, b: i64, c: i64, d: i64) -> TokenSummary {
    TokenSummary {
        input_tokens: a,
        output_tokens: b,
        cached_tokens: c,
        total_tokens: d,
        cache_rate: if a == 0 {
            None
        } else {
            Some(c as f64 / a as f64)
        },
    }
}

#[cfg(test)]
mod tests {
    use super::range_for_accounts;
    use crate::{dao::usage_dao, database::connect, model::usage_record::UsageRecord};
    use chrono::{TimeZone, Utc};

    #[tokio::test]
    async fn aggregates_today_tokens_for_all_accounts_in_one_query() {
        let path =
            std::env::temp_dir().join(format!("aimux-statistics-{}.sqlite3", uuid::Uuid::new_v4()));
        let pool = connect(&path).await.expect("创建数据库失败");
        for (id, account_id, input, output, cached, total) in [
            ("record-a", "account-a", 100_i64, 20_i64, 80_i64, 120_i64),
            ("record-b", "account-b", 200_i64, 30_i64, 100_i64, 230_i64),
        ] {
            usage_dao::create(
                &pool,
                &UsageRecord {
                    id: id.to_owned(),
                    trace_id: format!("trace-{id}"),
                    started_at: "2026-08-17T12:00:00Z".to_owned(),
                    ended_at: None,
                    duration_ms: None,
                    first_token_ms: None,
                    account_id: Some(account_id.to_owned()),
                    account_name: None,
                    account_type: None,
                    model: None,
                    reasoning_effort: None,
                    endpoint: None,
                    stream: false,
                    success: true,
                    status_code: None,
                    error_code: None,
                    error_message: None,
                    input_tokens: Some(input),
                    output_tokens: Some(output),
                    total_tokens: Some(total),
                    cached_tokens: Some(cached),
                    client_ip: None,
                    attempts: 1,
                },
            )
            .await
            .expect("写入使用记录失败");
        }
        let start = Utc.with_ymd_and_hms(2026, 8, 17, 0, 0, 0).single().unwrap();
        let end = Utc.with_ymd_and_hms(2026, 8, 18, 0, 0, 0).single().unwrap();
        let summaries = range_for_accounts(&pool, start, end)
            .await
            .expect("聚合账号 Token 失败");
        assert_eq!(summaries.len(), 2);
        assert_eq!(summaries["account-a"].total_tokens, 120);
        assert_eq!(summaries["account-b"].cached_tokens, 100);
        pool.close().await;
        let _ = std::fs::remove_file(path);
    }
}
