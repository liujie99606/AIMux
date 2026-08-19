use aimux_lib::upstream::client::upstream_url;

#[test]
fn preserves_existing_v1_prefix() {
    let url = upstream_url("https://example.com/v1", "/v1/chat/completions").unwrap();
    assert_eq!(url.as_str(), "https://example.com/v1/chat/completions");
}

#[test]
fn adds_v1_prefix_when_base_url_has_no_path() {
    let url = upstream_url("https://example.com", "/v1/chat/completions").unwrap();
    assert_eq!(url.as_str(), "https://example.com/v1/chat/completions");
}

#[test]
fn preserves_path_prefix_for_anthropic_endpoint() {
    let url = upstream_url("https://example.com/proxy/v1/", "/v1/messages").unwrap();
    assert_eq!(url.as_str(), "https://example.com/proxy/v1/messages");
}
