---
name: aimux-windows-release
description: AIMux Windows/Tauri 打包和发版规范。用户要求构建 Windows 安装包、升级版本或验证发布产物时使用。
---

# AIMux Windows 发版

1. 检查 Git 状态、当前版本和构建工具：

   ```powershell
   git status --short
   git log -1 --oneline
   Select-String -Path src-tauri/Cargo.toml -Pattern '^version = '
   where.exe node
   where.exe cargo
   ```

2. 用户明确提供版本号时，按下面的清单同步升级版本。项目版本是单一发布版本，以下五个文件必须一致：

   - `package.json`：前端项目版本。
   - `package-lock.json`：同步根对象的 `version` 和 `packages[""].version`；只更新项目版本，不手工改依赖版本。
   - `src-tauri/Cargo.toml`：`[package]` 的 `version`。
   - `src-tauri/Cargo.lock`：根项目 `[[package]]` 的 `version`，优先通过 `cargo check`、`cargo build` 或 Tauri 构建命令生成，不直接批量替换其他依赖版本。
   - `src-tauri/tauri.conf.json`：顶层 `version`，用于 Tauri 应用和安装包元数据。

   `src/stores/app.ts` 不需要手工改版本号：正式桌面端通过 Rust 的 `app_version` command 读取 Tauri 版本，浏览器开发模式由 Vite 注入 `package.json` 版本。升级后使用 `rg` 搜索旧版本，确认没有遗漏的硬编码发布版本。

3. 版本升级后的最小核对顺序：

   ```powershell
   npm install --package-lock-only
   cargo check --manifest-path src-tauri/Cargo.toml
   npm run format:check
   npm run build
   cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
   git diff --check
   ```

   如果 `Cargo.lock` 没有随项目版本更新，先运行一次 `cargo check` 再检查；不要为了版本升级执行全量清理。

4. 发布前确认版本和 Git 状态：

   ```powershell
   git status --short
   git log -1 --oneline
   rg -n '"version"|^version = ' package.json package-lock.json src-tauri/Cargo.toml src-tauri/Cargo.lock src-tauri/tauri.conf.json
   git diff --check
   ```

   版本号应替换为本次实际发布版本。确认提交后，将 `main` 推送，并创建与推送同名 tag（例如 `v0.2.4`）；GitHub Actions 以 `v*` tag 触发正式构建和 Release。除非用户明确要求，不自动执行 commit、push 或创建 tag。

5. 打包前确认 `dist`、`src-tauri/target` 和正在运行的 AIMux 进程状态。普通构建保留增量缓存；只有用户明确要求或增量缓存损坏时才全量清理。
6. 提醒用户执行：

   ```text
   请双击 scripts\windows\stable_build_windows.bat
   ```

   产物通常位于 `release\AIMux-Windows-x64.exe` 或 `release\AIMux-Windows-arm64.exe`。

不要自动执行 `git commit`、`git push`、创建 tag、安装验证或上传发布物，除非用户另行明确要求。数据库结构变化另遵守 `../aimux-database-migrations/SKILL.md`。
