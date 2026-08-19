use aimux_lib::config::Settings;

#[test]
fn database_path_always_uses_aimux_db() {
    let path = Settings::default().database_path();
    assert_eq!(
        path.file_name().and_then(|name| name.to_str()),
        Some("aimux.db")
    );
    assert_eq!(path.parent(), Some(Settings::data_dir().as_path()));
}
