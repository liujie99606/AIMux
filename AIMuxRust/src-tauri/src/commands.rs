use tauri::State;

use crate::app_state::AppState;

const GITHUB_REPOSITORY_URL: &str = "https://github.com/quietforge-dev/AIMux";

#[tauri::command]
pub fn open_data_directory() -> Result<(), String> {
    let path = crate::config::Settings::data_dir();
    std::fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    #[cfg(target_os = "windows")]
    std::process::Command::new("explorer")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    std::process::Command::new("open")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;
    #[cfg(target_os = "linux")]
    std::process::Command::new("xdg-open")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn open_external_url(url: String) -> Result<(), String> {
    if url != GITHUB_REPOSITORY_URL && !url.starts_with("https://github.com/quietforge-dev/AIMux/")
    {
        return Err("只允许打开 AIMux 的 GitHub 地址".into());
    }
    #[cfg(target_os = "windows")]
    std::process::Command::new("cmd")
        .args(["/C", "start", "", &url])
        .spawn()
        .map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    std::process::Command::new("open")
        .arg(&url)
        .spawn()
        .map_err(|e| e.to_string())?;
    #[cfg(target_os = "linux")]
    std::process::Command::new("xdg-open")
        .arg(&url)
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn app_version(_state: State<'_, std::sync::Arc<AppState>>) -> String {
    env!("CARGO_PKG_VERSION").to_owned()
}
