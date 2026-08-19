use aimux_lib::database::connect;
use sha2::{Digest, Sha384};

fn checksum(source: &[u8]) -> Vec<u8> {
    Sha384::digest(source).to_vec()
}

fn normalize_line_endings(source: &[u8]) -> Vec<u8> {
    source
        .iter()
        .enumerate()
        .filter_map(|(index, byte)| {
            if *byte == b'\r' && source.get(index + 1) == Some(&b'\n') {
                None
            } else {
                Some(*byte)
            }
        })
        .collect()
}

fn crlf_line_endings(source: &[u8]) -> Vec<u8> {
    let mut result = Vec::with_capacity(source.len());
    for byte in source {
        if *byte == b'\n' {
            result.push(b'\r');
        }
        result.push(*byte);
    }
    result
}

#[tokio::test]
async fn creates_and_reopens_baseline_database() {
    let path = std::env::temp_dir().join(format!("aimux-rust-{}.sqlite3", uuid::Uuid::new_v4()));
    let pool = connect(&path).await.expect("创建数据库失败");
    let count: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='accounts'",
    )
    .fetch_one(&pool)
    .await
    .expect("读取表失败");
    assert_eq!(count, 1);
    pool.close().await;
    let pool = connect(&path).await.expect("重新打开数据库失败");
    let migration: i64 =
        sqlx::query_scalar("SELECT COUNT(*) FROM _sqlx_migrations WHERE version=1 AND success=1")
            .fetch_one(&pool)
            .await
            .expect("读取迁移元数据失败");
    assert_eq!(migration, 1);
    pool.close().await;
    let _ = std::fs::remove_file(path);
}

#[tokio::test]
async fn accepts_migration_checksum_difference_caused_only_by_line_endings() {
    let path =
        std::env::temp_dir().join(format!("aimux-migration-{}.sqlite3", uuid::Uuid::new_v4()));
    let pool = connect(&path).await.expect("创建数据库失败");
    let source = include_bytes!("../migrations/0004_accounts_monitor_average_duration.sql");
    let lf_source = normalize_line_endings(source);
    let crlf_source = crlf_line_endings(&lf_source);
    let alternate_checksum = if checksum(source) == checksum(&lf_source) {
        checksum(&crlf_source)
    } else {
        checksum(&lf_source)
    };
    sqlx::query("UPDATE _sqlx_migrations SET checksum = ? WHERE version = 4")
        .bind(alternate_checksum)
        .execute(&pool)
        .await
        .expect("写入迁移校验和失败");
    pool.close().await;
    let reopened = connect(&path).await.expect("换行符兼容后打开数据库失败");
    let saved: Vec<u8> =
        sqlx::query_scalar("SELECT checksum FROM _sqlx_migrations WHERE version = 4")
            .fetch_one(&reopened)
            .await
            .expect("读取迁移校验和失败");
    assert_eq!(saved, checksum(source));
    reopened.close().await;
    let _ = std::fs::remove_file(path);
}
