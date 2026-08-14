use axum::http::HeaderMap;

pub fn passthrough(headers: &HeaderMap, names: &[&str]) -> Vec<(String, String)> {
    names
        .iter()
        .filter_map(|name| {
            headers
                .get(*name)
                .and_then(|value| value.to_str().ok())
                .map(|value| ((*name).into(), value.into()))
        })
        .collect()
}
