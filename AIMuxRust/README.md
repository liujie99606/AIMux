# AIMux Rust

这是 AIMux 的 Rust/Tauri 2 重构实现，前端使用 Vue 3 + Vite + Element Plus + Pinia，后端使用 Axum + Tokio + Reqwest + SQLx + SQLite。

## 本地开发

```powershell
npm install
npm run tauri dev
```

只调试前端：

```powershell
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
