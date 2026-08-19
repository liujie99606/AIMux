use aimux_lib::gateway::dto::{reasoning_effort, stream_outcome, usage, usage_from_sse};
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
        usage(
            &json!({"response":{"usage":{"input_tokens":4683,"output_tokens":5,"total_tokens":4688,"input_tokens_details":{"cached_tokens":3840}}}})
        ),
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
        usage(
            &json!({"usage":null,"response":{"usage":{"input_tokens":10,"output_tokens":2,"input_tokens_details":{"cached_tokens":8}}}})
        ),
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

#[test]
fn detects_protocol_completion_events() {
    assert_eq!(stream_outcome(b"data: [DONE]\n"), Some(true));
    assert_eq!(
        stream_outcome(br#"data: {"type":"response.completed","response":{}}"#),
        Some(true)
    );
    assert_eq!(
        stream_outcome(br#"data: {"type":"message_stop"}"#),
        Some(true)
    );
    assert_eq!(
        stream_outcome(br#"data: {"choices":[{"finish_reason":"stop"}]}"#),
        None
    );
    assert_eq!(
        stream_outcome(br#"data: {"type":"response.failed"}"#),
        Some(false)
    );
    assert_eq!(stream_outcome(b"event: response.completed\n"), None);
    assert_eq!(
        stream_outcome(b"event: response.completed\ndata: {\"response\":{}}\n"),
        Some(true)
    );
    assert_eq!(
        stream_outcome(br#"data: {"type":"response.output_text.delta"}"#),
        None
    );
}

#[test]
fn keeps_usage_after_chat_completion_finish_reason() {
    let body = br#"data: {"choices":[{"finish_reason":"stop"}]}

data: {"choices":[],"usage":{"prompt_tokens":100,"completion_tokens":4,"total_tokens":104,"prompt_tokens_details":{"cached_tokens":80}}}

data: [DONE]
"#;
    assert_eq!(stream_outcome(body), Some(true));
    assert_eq!(
        usage_from_sse(body),
        (Some(100), Some(4), Some(104), Some(80))
    );
}
