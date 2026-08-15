$projectRoot = Split-Path -Parent $PSScriptRoot

$env:AIMUX_PORT = '7790'
$env:AIMUX_MONITORING_ENABLED = 'false'
Set-Location (Join-Path $projectRoot 'src-tauri')
cargo run --bin aimux-gateway
