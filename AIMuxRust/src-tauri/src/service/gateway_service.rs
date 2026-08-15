use std::time::Instant;

use axum::{
    body::Body,
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
};
use futures_util::StreamExt;
use serde_json::{json, Value};
use sqlx::SqlitePool;
use uuid::Uuid;

use crate::{
    config::Settings,
    dao::{account_dao, usage_dao},
    error::AppError,
    gateway::dto,
    model::usage_record::UsageRecord,
    service::{account_service, model_service},
};

pub async fn forward(
    pool: &SqlitePool,
    settings: &Settings,
    body: Value,
    endpoint: &str,
    kind: &str,
    headers: HeaderMap,
) -> Result<Response, AppError> {
    let requested = dto::model(&body).map(str::to_owned);
    let reasoning_effort = dto::reasoning_effort(&body);
    let request_started = Instant::now();
    let max_attempts = settings.request_retry_attempts.clamp(1, 20) as i64;
    let trace_id = Uuid::new_v4().to_string();
    let mut last = (
        StatusCode::BAD_GATEWAY,
        "upstream_error".to_owned(),
        "上游请求失败".to_owned(),
    );
    for attempt in 1..=max_attempts {
        let Some(account) = account_dao::pick_one(pool, requested.as_deref(), kind).await? else {
            break;
        };
        account_dao::mark_used(pool, &account.id).await?;
        // Keep the client request immutable. A model mapping belongs only to this
        // account and must not leak into a later retry with another account.
        let mut upstream_body = body.clone();
        if let Some(upstream) = account_service::mapping(&account, requested.as_deref()) {
            if let Some(object) = upstream_body.as_object_mut() {
                object.insert("model".into(), Value::String(upstream));
            }
        }
        let started = Instant::now();
        let passthrough = crate::gateway::auth::passthrough(
            &headers,
            if kind == "anthropic" {
                &[
                    "anthropic-beta",
                    "anthropic-dangerous-direct-browser-access",
                ]
            } else {
                &["openai-beta", "idempotency-key"]
            },
        );
        let response = match crate::upstream::client::post(
            &account,
            endpoint,
            &upstream_body,
            settings,
            &passthrough,
        )
        .await
        {
            Ok(value) => value,
            Err(error) => {
                tracing::error!(
                    trace_id = %trace_id,
                    account_id = %account.id,
                    account_name = %account.name,
                    attempt,
                    %error,
                    "网关上游请求失败"
                );
                last = (
                    StatusCode::BAD_GATEWAY,
                    "upstream_connection_error".into(),
                    error.to_string(),
                );
                record(
                    pool,
                    &trace_id,
                    &account,
                    requested.as_deref(),
                    endpoint,
                    false,
                    Some(502),
                    Some(&last.1),
                    Some(&last.2),
                    attempt,
                    started,
                    None,
                    reasoning_effort.as_deref(),
                    None,
                )
                .await?;
                account_service::record_failure(pool, &account.id, Some(&last.1), Some(&last.2))
                    .await?;
                continue;
            }
        };
        let status = response.status();
        let content_type = response
            .headers()
            .get("content-type")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("application/json")
            .to_owned();
        if !status.is_success() {
            let bytes = response.bytes().await.unwrap_or_default();
            let message = String::from_utf8_lossy(&bytes[..bytes.len().min(4096)]).to_string();
            tracing::error!(
                trace_id = %trace_id,
                account_id = %account.id,
                account_name = %account.name,
                attempt,
                status_code = status.as_u16(),
                "网关上游响应失败"
            );
            last = (
                StatusCode::from_u16(status.as_u16()).unwrap_or(StatusCode::BAD_GATEWAY),
                "upstream_error".into(),
                message.clone(),
            );
            record(
                pool,
                &trace_id,
                &account,
                requested.as_deref(),
                endpoint,
                false,
                Some(status.as_u16() as i64),
                Some("upstream_error"),
                Some(&message),
                attempt,
                started,
                None,
                reasoning_effort.as_deref(),
                None,
            )
            .await?;
            account_service::record_failure(
                pool,
                &account.id,
                Some("upstream_error"),
                Some(&message),
            )
            .await?;
            continue;
        }
        if upstream_body
            .get("stream")
            .and_then(Value::as_bool)
            .unwrap_or(false)
        {
            let mut upstream = response.bytes_stream();
            let stream_record = UsageRecord {
                id: Uuid::new_v4().to_string(),
                trace_id: trace_id.clone(),
                started_at: started_at(started),
                ended_at: None,
                duration_ms: None,
                first_token_ms: None,
                account_id: Some(account.id.clone()),
                account_name: Some(account.name.clone()),
                account_type: Some(account.r#type.clone()),
                model: requested.clone(),
                reasoning_effort: reasoning_effort.clone(),
                endpoint: Some(endpoint.to_owned()),
                stream: true,
                success: false,
                status_code: Some(status.as_u16() as i64),
                error_code: None,
                error_message: None,
                input_tokens: None,
                output_tokens: None,
                total_tokens: None,
                cached_tokens: None,
                client_ip: None,
                attempts: attempt,
            };
            let stream_record_id = stream_record.id.clone();
            let stream_record_id = match usage_dao::create(pool, &stream_record).await {
                Ok(()) => Some(stream_record_id),
                Err(error) => {
                    tracing::error!(
                        trace_id = %trace_id,
                        account_id = %account.id,
                        %error,
                        "流式使用记录初始写入失败"
                    );
                    None
                }
            };
            let pool_for_stream = pool.clone();
            let account_for_stream = account.clone();
            let trace_for_stream = trace_id.clone();
            let model_for_stream = requested.clone();
            let endpoint_for_stream = endpoint.to_owned();
            let started_for_stream = started;
            let request_started_for_stream = request_started;
            let status_for_stream = status.as_u16() as i64;
            let reasoning_for_stream = reasoning_effort.clone();
            let stream_timeout =
                std::time::Duration::from_secs(settings.upstream_timeout_seconds.max(1));
            let (tx, mut rx) =
                tokio::sync::mpsc::channel::<Result<axum::body::Bytes, std::io::Error>>(16);
            tokio::spawn(async move {
                let mut captured = Vec::new();
                let mut first_token_ms = None;
                let mut stream_error: Option<String> = None;
                loop {
                    let next = tokio::time::timeout(stream_timeout, upstream.next()).await;
                    match next {
                        Ok(Some(Ok(chunk))) => {
                            captured.extend_from_slice(&chunk);
                            if !chunk.is_empty() && first_token_ms.is_none() {
                                first_token_ms =
                                    Some(request_started_for_stream.elapsed().as_millis() as i64);
                            }
                            let sent =
                                tokio::time::timeout(stream_timeout, tx.send(Ok(chunk))).await;
                            if !matches!(sent, Ok(Ok(()))) {
                                stream_error = Some("下游客户端已断开或读取超时".to_owned());
                                break;
                            }
                            if let Some(outcome) = dto::stream_outcome(&captured) {
                                if !outcome {
                                    stream_error = Some("上游返回流式失败事件".to_owned());
                                }
                                break;
                            }
                        }
                        Ok(Some(Err(error))) => {
                            let message = error.to_string();
                            stream_error = Some(message.clone());
                            let _ = tx.try_send(Err(std::io::Error::other(message)));
                            break;
                        }
                        Ok(None) => break,
                        Err(_) => {
                            let message = "上游流读取超时".to_owned();
                            stream_error = Some(message.clone());
                            let _ = tx.try_send(Err(std::io::Error::other(message)));
                            break;
                        }
                    }
                }
                let tokens = dto::usage_from_sse(&captured);
                let success = stream_error.is_none();
                let error_message = stream_error.as_deref();
                let error_code = if success {
                    None
                } else {
                    Some("stream_read_error")
                };
                let persisted = if let Some(id) = stream_record_id.as_deref() {
                    match usage_dao::finish_stream(
                        &pool_for_stream,
                        id,
                        &now(),
                        started_for_stream.elapsed().as_millis() as i64,
                        first_token_ms,
                        success,
                        Some(status_for_stream),
                        error_code,
                        error_message,
                        tokens,
                    )
                    .await
                    {
                        Ok(()) => {
                            if let Some(total) = tokens.2 {
                                let _ = sqlx::query(
                                    "UPDATE accounts SET total_tokens=total_tokens+? WHERE id=?",
                                )
                                .bind(total)
                                .bind(&account_for_stream.id)
                                .execute(&pool_for_stream)
                                .await;
                            }
                            true
                        }
                        Err(error) => {
                            tracing::error!(
                                trace_id = %trace_for_stream,
                                account_id = %account_for_stream.id,
                                %error,
                                "流式使用记录更新失败"
                            );
                            false
                        }
                    }
                } else if let Err(error) = record(
                    &pool_for_stream,
                    &trace_for_stream,
                    &account_for_stream,
                    model_for_stream.as_deref(),
                    &endpoint_for_stream,
                    success,
                    Some(status_for_stream),
                    error_code,
                    error_message,
                    attempt,
                    started_for_stream,
                    first_token_ms,
                    reasoning_for_stream.as_deref(),
                    Some(tokens),
                )
                .await
                {
                    tracing::error!(%error, "流式使用记录写入失败");
                    false
                } else {
                    true
                };
                if persisted && success {
                    let _ =
                        account_service::record_success(&pool_for_stream, &account_for_stream.id)
                            .await;
                } else {
                    let _ = account_service::record_failure(
                        &pool_for_stream,
                        &account_for_stream.id,
                        error_code,
                        error_message,
                    )
                    .await;
                }
            });
            let streamed: futures_util::stream::BoxStream<
                'static,
                Result<axum::body::Bytes, std::io::Error>,
            > = async_stream::stream! {
                while let Some(item) = rx.recv().await {
                    yield item;
                }
            }
            .boxed();
            let response = Response::builder()
                .status(status)
                .header("content-type", content_type)
                .body(Body::from_stream(streamed))
                .map_err(|e| AppError::Internal(e.to_string()))?;
            return Ok(response);
        }
        let bytes = response
            .bytes()
            .await
            .map_err(|e| AppError::Upstream(e.to_string()))?;
        let payload = serde_json::from_slice::<Value>(&bytes).unwrap_or(Value::Null);
        record(
            pool,
            &trace_id,
            &account,
            requested.as_deref(),
            endpoint,
            true,
            Some(status.as_u16() as i64),
            None,
            None,
            attempt,
            started,
            None,
            reasoning_effort.as_deref(),
            Some(dto::usage(&payload)),
        )
        .await?;
        account_service::record_success(pool, &account.id).await?;
        return Response::builder()
            .status(status)
            .header("content-type", content_type)
            .body(Body::from(bytes))
            .map_err(|e| AppError::Internal(e.to_string()));
    }
    Ok((
        last.0,
        axum::Json(json!({"error":{"message":last.2,"type":last.1}})),
    )
        .into_response())
}

async fn record(
    pool: &SqlitePool,
    trace_id: &str,
    account: &crate::model::account::Account,
    model: Option<&str>,
    endpoint: &str,
    success: bool,
    status: Option<i64>,
    code: Option<&str>,
    message: Option<&str>,
    attempt: i64,
    started: Instant,
    first_token_ms: Option<i64>,
    reasoning_effort: Option<&str>,
    tokens: Option<(Option<i64>, Option<i64>, Option<i64>, Option<i64>)>,
) -> Result<(), AppError> {
    let (input, output, total, cached) = tokens.unwrap_or((None, None, None, None));
    let duration_ms = started.elapsed().as_millis() as i64;
    let ended_at = now();
    let started_at = started_at(started);
    let record = UsageRecord {
        id: Uuid::new_v4().to_string(),
        trace_id: trace_id.into(),
        started_at,
        ended_at: Some(ended_at),
        duration_ms: Some(duration_ms),
        first_token_ms,
        account_id: Some(account.id.clone()),
        account_name: Some(account.name.clone()),
        account_type: Some(account.r#type.clone()),
        model: model.map(str::to_owned),
        reasoning_effort: reasoning_effort.map(str::to_owned),
        endpoint: Some(endpoint.into()),
        stream: false,
        success,
        status_code: status,
        error_code: code.map(str::to_owned),
        error_message: message.map(str::to_owned),
        input_tokens: input,
        output_tokens: output,
        total_tokens: total,
        cached_tokens: cached,
        client_ip: None,
        attempts: attempt,
    };
    usage_dao::create(pool, &record).await?;
    if let Some(tokens) = total {
        sqlx::query("UPDATE accounts SET total_tokens=total_tokens+? WHERE id=?")
            .bind(tokens)
            .bind(&account.id)
            .execute(pool)
            .await?;
    }
    Ok(())
}

fn started_at(started: Instant) -> String {
    chrono::Utc::now()
        .checked_sub_signed(chrono::Duration::milliseconds(
            started.elapsed().as_millis() as i64,
        ))
        .unwrap_or_else(chrono::Utc::now)
        .format("%Y-%m-%dT%H:%M:%SZ")
        .to_string()
}

pub async fn models(pool: &SqlitePool, kind: &str) -> Result<Value, AppError> {
    let items = model_service::list(pool, Some(kind)).await?;
    Ok(
        json!({"object":"list","data":items.into_iter().map(|model|json!({"id":model.name,"object":"model","owned_by":"aimux"})).collect::<Vec<_>>() }),
    )
}

fn now() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}
