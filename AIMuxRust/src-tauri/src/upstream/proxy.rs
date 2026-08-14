use crate::config::Settings;

pub fn proxy(settings: &Settings) -> Result<Option<reqwest::Proxy>, reqwest::Error> {
    if !settings.upstream_proxy_enabled || settings.upstream_proxy_url.trim().is_empty() {
        return Ok(None);
    }
    Ok(Some(reqwest::Proxy::all(
        settings.upstream_proxy_url.trim(),
    )?))
}
