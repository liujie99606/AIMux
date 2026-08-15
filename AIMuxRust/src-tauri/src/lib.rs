#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app_state;
mod background;
mod commands;
mod config;
mod controller;
mod dao;
mod database;
mod error;
mod gateway;
mod logging;
mod model;
mod schema;
mod service;
mod upstream;

use std::sync::Arc;

use app_state::AppState;
use config::Settings;
use tauri::Manager;

pub fn run() {
    logging::init();
    let settings = Settings::load().unwrap_or_default();
    let runtime = tokio::runtime::Runtime::new().expect("创建 Tokio runtime 失败");
    let state = runtime.block_on(async {
        AppState::initialize(settings)
            .await
            .expect("初始化 AIMux 失败")
    });
    let shared = Arc::new(state);
    let monitor_state = Arc::clone(&shared);
    runtime.spawn(async move {
        background::monitor_task::run(monitor_state).await;
    });
    let server_state = Arc::clone(&shared);
    runtime.spawn(async move {
        if let Err(error) = controller::serve(server_state).await {
            tracing::error!(%error, "AIMux HTTP 服务退出");
        }
    });
    tauri::Builder::default()
        .manage(shared)
        .invoke_handler(tauri::generate_handler![
            commands::open_data_directory,
            commands::open_external_url,
            commands::app_version
        ])
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_title("AIMux");
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}

pub fn run_gateway() -> Result<(), String> {
    logging::init();
    let settings = Settings::load().map_err(|error| format!("读取设置失败: {error}"))?;
    let runtime = tokio::runtime::Runtime::new().map_err(|error| error.to_string())?;
    let state = runtime
        .block_on(async { AppState::initialize(settings).await })
        .map_err(|error| format!("初始化 AIMux 失败: {error}"))?;
    let shared = Arc::new(state);
    let monitor_state = Arc::clone(&shared);
    runtime.spawn(async move {
        background::monitor_task::run(monitor_state).await;
    });
    runtime
        .block_on(controller::serve(shared))
        .map_err(|error| format!("AIMux HTTP 服务退出: {error}"))
}
