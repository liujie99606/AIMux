use aimux_lib::{
    dao::usage_dao, database::connect, model::usage_record::UsageRecord,
    service::statistics_service::range_for_accounts,
};
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
