---
name: aimux-windows-release
description: AIMux Windows 简化发版流程。用户要求发版、升级版本、准备打包或发布安装包时使用：检查 Git 状态、确认或修改 pyproject.toml 版本号，然后提醒用户执行 scripts/win_release.bat。
---

# AIMux Windows 发版

只执行以下三步，不自行扩展测试、安装验证、上传或推送流程：

1. 检查 Git 状态和当前版本：

   ```powershell
   git status --short
   git log -1 --oneline
   Select-String -Path pyproject.toml -Pattern '^version = '
   ```

   有未提交改动时，先向用户说明。不要覆盖或隐藏用户改动。

2. 确认发版版本号并修改 `../../../pyproject.toml` 的 `[project].version`。

   用户没有提供目标版本时，先报告当前版本并询问，不要自行猜版本号。版本号只维护这一处，发布脚本会自动读取它。

3. 提醒用户执行：

   ```text
   请双击 scripts\win_release.bat
   ```

   该脚本会自动全量构建应用，并根据本机架构生成 `release\AIMux-Windows-x64.exe` 或 `release\AIMux-Windows-arm64.exe`。

不要自动执行 `win_release.bat`、`git commit`、`git push`、安装验证或上传发布物，除非用户另行明确要求。涉及数据库结构时，另遵守 `../aimux-database-migrations/SKILL.md`。
