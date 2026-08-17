# AIMux Rust

这是 AIMux 的 Rust/Tauri 2 重构实现，前端使用 Vue 3 + Vite + Element Plus + Pinia，后端使用 Axum + Tokio + Reqwest + SQLx + SQLite。

完整启动方式和端口隔离说明：[开发启动与端口说明](开发启动与端口说明.md)

## 本地开发

端口配置集中在 `config/runtime-ports.json`：稳定模式是后端 `7789`、浏览器前端 `1420`；开发模式是后端 `7790`、浏览器前端 `1421`。

正式 Tauri 安装版的前端嵌入应用，不启动 Vite，因此没有实际的 `1420` 或 `1421` 监听端口；正式版内置网关使用 `7789`。

日常页面开发只启动 Vite，热更新不会编译或重启 Rust 网关：

```powershell
npm install
npm run dev
```

不设置模式时，`npm run dev` 使用稳定前端端口 `1420`。也可以双击 `scripts/windows/start_frontend_stable.bat`，它会读取配置并连接稳定网关 `7789`。

后端改动需编译，但使用独立的 `7790` 开发网关和同一个 `aimux.db`（默认关闭监控），不会中断稳定网关或 Codex：

```powershell
npm run dev:gateway
```

Rust 始终使用系统数据目录下的 `aimux.db`，稳定网关和开发网关不区分数据库；设置页不再提供数据库路径切换。旧配置文件中遗留的 `db_path` 不会生效。

另开一个 PowerShell 窗口，让前端连接开发网关（端口 `1421`）：

```powershell
$env:VITE_API_BASE = 'http://127.0.0.1:7790'
$env:AIMUX_RUNTIME_MODE = 'development'
npm run dev
```

也可以直接双击 `scripts/windows/start_frontend.bat`，它会读取配置并连接开发网关 `7790`。

Rust 检查和数据库兼容测试：

```powershell
cd src-tauri
cargo fmt -- --check
cargo test --lib
cargo check
```

## Windows 打包

双击 `scripts/windows/build_windows.bat`。脚本会检查 Node.js 与 Rust 工具链，在首次打包时安装 npm 依赖，再通过 Tauri 生成 Windows NSIS 单文件安装包。

产物位于：

```text
release\AIMux-Windows-x64.exe
```

ARM64 Windows 会生成 `release\AIMux-Windows-arm64.exe`。打包采用 Rust/Tauri 的增量构建，不会清理 `src-tauri\target` 缓存。

首次启动时，空数据库执行 `src-tauri/migrations/0001_baseline.sql`；已有 AIMux SQLite 数据库只接管 SQLx 的 `_sqlx_migrations` 元数据，不修改业务表、旧数据或 `alembic_version`。后续结构变化只追加新的 SQL migration。
