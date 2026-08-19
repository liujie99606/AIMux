use std::{io, time::Duration};

use aimux_lib::service::gateway_service::{wait_for_first_chunk, FirstChunkError};
use axum::{body::Bytes, http::StatusCode};
use futures_util::stream;

#[tokio::test]
async fn waits_past_empty_chunks_for_the_first_nonempty_chunk() {
    let expected = Bytes::from_static(b"data: first");
    let mut upstream = stream::iter(vec![
        Ok::<Bytes, io::Error>(Bytes::new()),
        Ok(expected.clone()),
    ]);
    let first = wait_for_first_chunk(&mut upstream, Duration::from_secs(1))
        .await
        .expect("应读取到首个非空数据块");
    assert_eq!(first, expected);
}

#[tokio::test]
async fn reports_a_timeout_before_the_first_chunk() {
    let mut upstream = stream::pending::<Result<Bytes, io::Error>>();
    let error = wait_for_first_chunk(&mut upstream, Duration::from_millis(10))
        .await
        .expect_err("首字超时应失败");
    assert!(matches!(error, FirstChunkError::Timeout));
    assert_eq!(error.error_code(), "first_token_timeout");
    assert_eq!(error.status_code(), StatusCode::GATEWAY_TIMEOUT);
}
