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

2. 用户明确提供版本号时，同时更新 `package.json` 和 `src-tauri/Cargo.toml`，并让 `package-lock.json` 与前端版本保持一致；没有版本号时先报告当前版本，不自行猜版本。
3. 打包前确认 `dist`、`src-tauri/target` 和正在运行的 AIMux 进程状态。普通构建保留增量缓存；只有用户明确要求或增量缓存损坏时才全量清理。
4. 提醒用户执行：

   ```text
   请双击 scripts\windows\stable_build_windows.bat
   ```

   产物通常位于 `release\AIMux-Windows-x64.exe` 或 `release\AIMux-Windows-arm64.exe`。

不要自动执行 `git commit`、`git push`、创建 tag、安装验证或上传发布物，除非用户另行明确要求。数据库结构变化另遵守 `../aimux-database-migrations/SKILL.md`。
