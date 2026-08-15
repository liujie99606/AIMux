# AIMux Rust

这是 AIMux 的 Rust/Tauri 2 重构实现，前端使用 Vue 3 + Vite + Element Plus + Pinia，后端使用 Axum + Tokio + Reqwest + SQLx + SQLite。

完整启动方式和端口隔离说明：[开发启动与端口说明](开发启动与端口说明.md)

## 本地开发

稳定网关使用 `7789`。日常页面开发只启动 Vite，热更新不会编译或重启 Rust 网关：

```powershell
npm install
npm run dev
```

后端改动需编译，但使用独立的 `7790` 开发网关和同一个 `aimux.db`（默认关闭监控），不会中断稳定网关或 Codex：

```powershell
npm run dev:gateway
```

Rust 始终使用系统数据目录下的 `aimux.db`，稳定网关和开发网关不区分数据库；设置页不再提供数据库路径切换。旧配置文件中遗留的 `db_path` 不会生效。

另开一个 PowerShell 窗口，让前端连接开发网关：

```powershell
$env:VITE_API_BASE = 'http://127.0.0.1:7790'
npm run dev
```

Rust 检查和数据库兼容测试：

```powershell
cd src-tauri
cargo fmt -- --check
cargo test --lib
cargo check
```

首次启动时，空数据库执行 `src-tauri/migrations/0001_baseline.sql`；已有 AIMux SQLite 数据库只接管 SQLx 的 `_sqlx_migrations` 元数据，不修改业务表、旧数据或 `alembic_version`。后续结构变化只追加新的 SQL migration。
