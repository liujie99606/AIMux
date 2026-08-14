use crate::config::Settings;

pub fn validate(settings: &Settings) -> Result<(), String> {
    if settings.port == 0 {
        return Err("端口必须大于 0".into());
    }
    Ok(())
}
