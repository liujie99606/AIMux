use aimux_lib::schema::account_schema::AccountUpdate;

#[test]
fn update_payload_accepts_explicit_empty_values() {
    let absent: AccountUpdate = serde_json::from_str("{}").expect("反序列化空更新请求");
    assert!(absent.notes.is_none());
    assert!(absent.model_mappings.is_none());

    let clear: AccountUpdate =
        serde_json::from_str(r#"{"notes":"","model_mappings":{},"tags":[]}"#)
            .expect("反序列化清空更新请求");
    assert_eq!(clear.notes.as_deref(), Some(""));
    assert!(clear
        .model_mappings
        .is_some_and(|value| value == serde_json::json!({})));
    assert_eq!(clear.tags, Some(Vec::new()));
}
