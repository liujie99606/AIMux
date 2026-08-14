use serde_json::Value;

pub fn model(body: &Value) -> Option<&str> {
    body.get("model").and_then(Value::as_str)
}
pub fn usage(body: &Value) -> (Option<i64>, Option<i64>, Option<i64>, Option<i64>) {
    let Some(u) = body.get("usage") else {
        return (None, None, None, None);
    };
    let input = u
        .get("prompt_tokens")
        .or_else(|| u.get("input_tokens"))
        .and_then(Value::as_i64);
    let output = u
        .get("completion_tokens")
        .or_else(|| u.get("output_tokens"))
        .and_then(Value::as_i64);
    let total = u
        .get("total_tokens")
        .and_then(Value::as_i64)
        .or_else(|| input.zip(output).map(|(a, b)| a + b));
    let cached = u
        .pointer("/prompt_tokens_details/cached_tokens")
        .or_else(|| u.pointer("/input_tokens_details/cached_tokens"))
        .and_then(Value::as_i64);
    (input, output, total, cached)
}

pub fn usage_from_sse(bytes: &[u8]) -> (Option<i64>, Option<i64>, Option<i64>, Option<i64>) {
    let text = String::from_utf8_lossy(bytes);
    let mut result = (None, None, None, None);
    for line in text.lines() {
        let Some(data) = line.strip_prefix("data:") else {
            continue;
        };
        let data = data.trim();
        if data == "[DONE]" {
            continue;
        }
        if let Ok(value) = serde_json::from_str::<Value>(data) {
            let current = usage(&value);
            if current.0.is_some()
                || current.1.is_some()
                || current.2.is_some()
                || current.3.is_some()
            {
                result = current;
            }
        }
    }
    result
}
