use crate::config::Settings;
use std::time::Duration;

pub fn request_timeout(settings: &Settings) -> Duration {
    Duration::from_secs(settings.upstream_timeout_seconds.max(1))
}
