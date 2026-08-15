use serde_json::Value;

pub fn model(body: &Value) -> Option<&str> {
    body.get("model").and_then(Value::as_str)
}

pub fn reasoning_effort(body: &Value) -> Option<String> {
    let effort = body
        .get("reasoning_effort")
        .filter(|value| !value.is_null())
        .or_else(|| body.get("reasoning").and_then(|value| value.get("effort")))?;
    effort.as_str().map(str::to_owned).or_else(|| {
        if effort.is_null() {
            None
        } else {
            Some(effort.to_string())
        }
    })
}

fn usage_object(body: &Value) -> Option<&Value> {
    [
        body.get("usage"),
        body.get("response").and_then(|value| value.get("usage")),
        body.get("message").and_then(|value| value.get("usage")),
    ]
    .into_iter()
    .flatten()
    .find(|value| value.is_object())
}

fn usage_fields(body: &Value) -> (Option<i64>, Option<i64>, Option<i64>, Option<i64>) {
    let Some(u) = usage_object(body) else {
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
    let total = u.get("total_tokens").and_then(Value::as_i64);
    let cached = u
        .get("cached_tokens")
        .or_else(|| u.pointer("/prompt_tokens_details/cached_tokens"))
        .or_else(|| u.pointer("/input_tokens_details/cached_tokens"))
        .and_then(Value::as_i64);
    (input, output, total, cached)
}

fn with_estimated_total(
    (input, output, total, cached): (Option<i64>, Option<i64>, Option<i64>, Option<i64>),
) -> (Option<i64>, Option<i64>, Option<i64>, Option<i64>) {
    let total = total.or_else(|| {
        (input.is_some() || output.is_some()).then(|| input.unwrap_or(0) + output.unwrap_or(0))
    });
    (input, output, total, cached)
}

pub fn usage(body: &Value) -> (Option<i64>, Option<i64>, Option<i64>, Option<i64>) {
    with_estimated_total(usage_fields(body))
}

pub fn usage_from_sse(bytes: &[u8]) -> (Option<i64>, Option<i64>, Option<i64>, Option<i64>) {
    let text = String::from_utf8_lossy(bytes);
    let mut result = (None, None, None, None);
    for line in text.lines() {
        let line = line.trim();
        let data = line.strip_prefix("data:").map(str::trim).unwrap_or(line);
        if data == "[DONE]" {
            continue;
        }
        if let Ok(value) = serde_json::from_str::<Value>(data) {
            merge_usage(&mut result, usage_fields(&value));
        }
    }
    with_estimated_total(result)
}

fn merge_usage(
    target: &mut (Option<i64>, Option<i64>, Option<i64>, Option<i64>),
    current: (Option<i64>, Option<i64>, Option<i64>, Option<i64>),
) {
    if current.0.is_some() {
        target.0 = current.0;
    }
    if current.1.is_some() {
        target.1 = current.1;
    }
    if current.2.is_some() {
        target.2 = current.2;
    }
    if current.3.is_some() {
        target.3 = current.3;
    }
}

#[cfg(test)]
mod tests {
    use super::{reasoning_effort, usage, usage_from_sse};
    use serde_json::json;

    #[test]
    fn reads_reasoning_effort_from_supported_request_shapes() {
        assert_eq!(
            reasoning_effort(&json!({"reasoning_effort": "high"})),
            Some("high".into())
        );
        assert_eq!(
            reasoning_effort(&json!({"reasoning": {"effort": "low"}})),
            Some("low".into())
        );
        assert_eq!(
            reasoning_effort(&json!({"reasoning_effort": null, "reasoning": {"effort": "medium"}})),
            Some("medium".into())
        );
        assert_eq!(reasoning_effort(&json!({})), None);
    }

    #[test]
    fn reads_nested_responses_usage_and_cached_tokens() {
        assert_eq!(
            usage(&json!({
                "response": {
                    "usage": {
                        "input_tokens": 4683,
                        "output_tokens": 5,
                        "total_tokens": 4688,
                        "input_tokens_details": {"cached_tokens": 3840}
                    }
                }
            })),
            (Some(4683), Some(5), Some(4688), Some(3840))
        );
    }

    #[test]
    fn merges_usage_fields_across_sse_events() {
        let body = br#"data: {"response":{"usage":{"input_tokens":12}}}

data: {"type":"response.completed","response":{"usage":{"output_tokens":3,"prompt_tokens_details":{"cached_tokens":5}}}}

data: [DONE]
"#;
        assert_eq!(usage_from_sse(body), (Some(12), Some(3), Some(15), Some(5)));
    }

    #[test]
    fn accepts_null_top_level_usage_and_bare_json_events() {
        assert_eq!(
            usage(&json!({
                "usage": null,
                "response": {
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "input_tokens_details": {"cached_tokens": 8}
                    }
                }
            })),
            (Some(10), Some(2), Some(12), Some(8))
        );
        assert_eq!(
            usage_from_sse(
                br#"{"response":{"usage":{"input_tokens":4,"output_tokens":1}}}
"#
            ),
            (Some(4), Some(1), Some(5), None)
        );
    }
}
