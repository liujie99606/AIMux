use axum::body::Body;
use futures_util::StreamExt;
use reqwest::Response;

pub fn body(response: Response) -> Body {
    Body::from_stream(
        response
            .bytes_stream()
            .map(|chunk| chunk.map_err(|e| std::io::Error::other(e.to_string()))),
    )
}
