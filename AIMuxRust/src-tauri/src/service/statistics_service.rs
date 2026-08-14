use crate::{dao::account_dao, error::AppError, schema::usage_schema::TokenSummary};
use chrono::{Duration, Local, TimeZone, Utc};
use sqlx::SqlitePool;

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
    let mut account_today = Vec::new();
    for account in accounts {
        let s = range_for_account(
            pool,
            &account.id,
            start_today,
            start_today + Duration::days(1),
        )
        .await?;
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
    let (a, b, c, d) = query(pool, start, end, None).await?;
    Ok(summary(a, b, c, d))
}
async fn range_for_account(
    pool: &SqlitePool,
    id: &str,
    start: chrono::DateTime<Utc>,
    end: chrono::DateTime<Utc>,
) -> Result<TokenSummary, AppError> {
    let (a, b, c, d) = query(pool, Some(start), Some(end), Some(id)).await?;
    Ok(summary(a, b, c, d))
}
async fn query(
    pool: &SqlitePool,
    start: Option<chrono::DateTime<Utc>>,
    end: Option<chrono::DateTime<Utc>>,
    account: Option<&str>,
) -> Result<(i64, i64, i64, i64), AppError> {
    let mut q=String::from("SELECT COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),COALESCE(SUM(cached_tokens),0),COALESCE(SUM(total_tokens),0) FROM usage_records WHERE 1=1");
    let mut vals = Vec::new();
    if let Some(s) = start {
        q.push_str(" AND started_at >= ?");
        vals.push(s.format("%Y-%m-%dT%H:%M:%SZ").to_string())
    }
    if let Some(e) = end {
        q.push_str(" AND started_at < ?");
        vals.push(e.format("%Y-%m-%dT%H:%M:%SZ").to_string())
    }
    if let Some(id) = account {
        q.push_str(" AND account_id=?");
        vals.push(id.into())
    }
    let mut query = sqlx::query_as::<_, (i64, i64, i64, i64)>(&q);
    for v in vals {
        query = query.bind(v);
    }
    Ok(query.fetch_one(pool).await?)
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
