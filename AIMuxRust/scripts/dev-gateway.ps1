$projectRoot = Split-Path -Parent $PSScriptRoot

$runtimeConfigPath = Join-Path $projectRoot 'config\runtime-ports.json'
if (-not (Test-Path $runtimeConfigPath)) {
    throw "找不到端口配置文件：$runtimeConfigPath"
}
$runtimeConfig = Get-Content -Raw $runtimeConfigPath | ConvertFrom-Json
$env:AIMUX_PORT = [string]$runtimeConfig.development.backend
$env:AIMUX_MONITORING_ENABLED = 'false'
Set-Location (Join-Path $projectRoot 'src-tauri')
cargo run --bin aimux-gateway
