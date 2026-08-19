use std::path::Path;

use sha2::{Digest, Sha384};
use sqlx::{
    migrate::Migrator,
    sqlite::{SqliteConnectOptions, SqlitePoolOptions},
    SqlitePool,
};

use crate::error::AppError;

static MIGRATOR: Migrator = sqlx::migrate!("./migrations");

pub async fn connect(path: &Path) -> Result<SqlitePool, AppError> {
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent)
            .await
            .map_err(|e| AppError::Internal(e.to_string()))?;
    }
    let options = SqliteConnectOptions::new()
        .filename(path)
        .create_if_missing(true)
        .foreign_keys(true);
    let pool = SqlitePoolOptions::new()
        .max_connections(8)
        .connect_with(options)
        .await?;
    sqlx::query("PRAGMA journal_mode = WAL")
        .execute(&pool)
        .await?;
    let has_accounts: bool = sqlx::query_scalar(
        "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts')",
    )
    .fetch_one(&pool)
    .await?;
    if !has_accounts {
        MIGRATOR.run(&pool).await?;
    } else {
        ensure_baseline_metadata(&pool).await?;
        ensure_placeholder_metadata(&pool).await?;
        ensure_line_ending_checksum(
            &pool,
            3,
            include_bytes!("../../migrations/0003_models_one_default.sql"),
        )
        .await?;
        ensure_line_ending_checksum(
            &pool,
            4,
            include_bytes!("../../migrations/0004_accounts_monitor_average_duration.sql"),
        )
        .await?;
        MIGRATOR.run(&pool).await?;
    }
    Ok(pool)
}

async fn ensure_baseline_metadata(pool: &SqlitePool) -> Result<(), AppError> {
    sqlx::query("CREATE TABLE IF NOT EXISTS _sqlx_migrations (version BIGINT PRIMARY KEY NOT NULL, description TEXT NOT NULL, installed_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, success BOOLEAN NOT NULL, checksum BLOB NOT NULL, execution_time BIGINT NOT NULL)").execute(pool).await?;
    let checksum = Sha384::digest(include_bytes!("../../migrations/0001_baseline.sql"));
    let existing_checksum: Option<Vec<u8>> =
        sqlx::query_scalar("SELECT checksum FROM _sqlx_migrations WHERE version = 1")
            .fetch_optional(pool)
            .await?;
    match existing_checksum {
        None => {
            sqlx::query("INSERT INTO _sqlx_migrations(version, description, success, checksum, execution_time) VALUES(1, 'baseline', 1, ?, 0)")
                .bind(checksum.as_slice())
                .execute(pool)
                .await?;
        }
        // 基线仅用于接管已有业务表；历史版本的基线内容可能不同，统一更新其元数据。
        Some(existing) if existing != checksum.as_slice() => {
            sqlx::query("UPDATE _sqlx_migrations SET checksum = ? WHERE version = 1")
                .bind(checksum.as_slice())
                .execute(pool)
                .await?;
        }
        Some(_) => {}
    }
    Ok(())
}

async fn ensure_placeholder_metadata(pool: &SqlitePool) -> Result<(), AppError> {
    let checksum = Sha384::digest(include_bytes!("../../migrations/0002_placeholder.sql"));
    let existing_checksum: Option<Vec<u8>> =
        sqlx::query_scalar("SELECT checksum FROM _sqlx_migrations WHERE version = 2")
            .fetch_optional(pool)
            .await?;
    if matches!(existing_checksum, Some(existing) if existing != checksum.as_slice()) {
        sqlx::query("UPDATE _sqlx_migrations SET checksum = ? WHERE version = 2")
            .bind(checksum.as_slice())
            .execute(pool)
            .await?;
    }
    Ok(())
}

async fn ensure_line_ending_checksum(
    pool: &SqlitePool,
    version: i64,
    source: &[u8],
) -> Result<(), AppError> {
    let existing: Option<Vec<u8>> =
        sqlx::query_scalar("SELECT checksum FROM _sqlx_migrations WHERE version = ?")
            .bind(version)
            .fetch_optional(pool)
            .await?;
    let Some(existing) = existing else {
        return Ok(());
    };

    let compiled_checksum = checksum(source);
    if existing == compiled_checksum {
        return Ok(());
    }

    let lf_source = normalize_line_endings(source);
    let crlf_source = crlf_line_endings(&lf_source);
    if existing == checksum(&lf_source) || existing == checksum(&crlf_source) {
        sqlx::query("UPDATE _sqlx_migrations SET checksum = ? WHERE version = ?")
            .bind(compiled_checksum)
            .bind(version)
            .execute(pool)
            .await?;
    }
    Ok(())
}

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
