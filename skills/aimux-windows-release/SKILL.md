---
name: aimux-windows-release
description: AIMux Windows 构建与发版规范。用户要求打包、生成安装包、发布新版、升级版本、验证 dist/release 产物、向其他用户分发 EXE，或排查 win_build/win_release/Inno Setup 发布问题时使用。覆盖版本确认、完整测试、Alembic 检查、PyInstaller、Inno Setup、安装升级验证和发布结果报告。
---

# AIMux Windows 发版规范

使用仓库现有 `scripts/win_release.bat`、`scripts/release_installer.py` 和 `installer/AIMux.iss`，不要另造发布流程。涉及数据库结构时，同时遵守 `../aimux-database-migrations/SKILL.md`。

## 区分任务

- **本地打包测试**：用户只要求“打包看看”时，不主动修改版本号；运行与其指定范围对应的构建脚本。
- **正式发版**：用户要求“发版、给其他用户、发布新版本”时，执行本文完整流程。
- **仅分析/说明**：用户只问发版方法时，仅说明，不修改版本、不构建、不提交。

## 正式发版流程

1. 检查工作区与版本：

   ```powershell
   git status --short
   git log -1 --oneline
   Select-String -Path pyproject.toml -Pattern '^version = '
   ```

   发现未提交改动时先确认来源和状态，不能覆盖或夹带用户改动。不要自行决定新版本号；用户未提供时先报告当前版本并请求目标版本。

2. 更新 `pyproject.toml` 的 `[project].version`。遵循语义化版本：

   - 修复且兼容：patch，例如 `0.1.0 -> 0.1.1`。
   - 向后兼容的新功能：minor，例如 `0.1.0 -> 0.2.0`。
   - 不兼容变化：major，例如 `0.x -> 1.0.0`，需用户明确确认。

   `release_installer.py` 会自动读取该版本；不要在批处理或安装器里再手工维护第二份版本。

3. 检查数据库变化：

   - 修改表、字段、类型、NULL、默认值、索引、约束或已有数据格式时，确认已经追加新的 Alembic revision。
   - 普通 CRUD、查询、排序、分页或 UI 改动不创建 migration。
   - 确认 `migrations/versions/` 单一 head，且 PyInstaller 仍打包 `migrations/`。

4. 执行发布前完整测试：

   ```powershell
   .\.venv\Scripts\python.exe -m pytest
   git diff --check
   ```

   任一失败都停止发版并修复，不能仅凭旧测试结果继续。

5. 按项目规范创建中文本地 commit，不推送。正式构建前再次确认 `git status --short` 为空，确保安装包对应一个可追溯提交。

6. 关闭所有 AIMux 实例，包括 `dist` 版、已安装版和系统托盘进程。可以只读检查：

   ```powershell
   Get-Process AIMux -ErrorAction SilentlyContinue
   ```

   不未经用户同意强制结束进程；被占用时提示用户从托盘退出。

7. 检查 Inno Setup：

   ```powershell
   .\.venv\Scripts\python.exe scripts\release_installer.py --check-only
   ```

   缺失时安装：

   ```powershell
   winget install --id JRSoftware.InnoSetup -e
   ```

8. 执行正式发布：

   ```powershell
   .\scripts\win_release.bat
   ```

   该脚本执行 `win_build.bat --clean`，生成 PyInstaller `onedir`，再输出单个 Inno Setup 安装包。不要把 PyInstaller 改成 `--onefile`。

9. 校验产物：

   ```powershell
   Get-Item release\AIMux-Setup-<版本>.exe
   Get-FileHash release\AIMux-Setup-<版本>.exe -Algorithm SHA256
   Get-AuthenticodeSignature release\AIMux-Setup-<版本>.exe
   ```

   确认文件存在、非零、时间为本轮构建。没有证书时签名状态为未签名，必须在交付说明中提示可能出现 SmartScreen；不能声称已签名。

10. 安装与升级验证：

   - 使用当前安装包完成一次本机安装或覆盖升级。
   - 启动已安装版，确认账号、模型、设置和历史数据仍来自 `%APPDATA%\aimux`。
   - 确认数据库 migration 成功、页面可加载、API 健康检查和一个核心请求正常。
   - 不同时运行 `dist` 版和安装版，避免端口冲突。
   - 安装或卸载默认不得删除 `%APPDATA%\aimux`。

## 产物与 Git

- 应用目录：`dist\AIMux\`。
- 对外安装包：`release\AIMux-Setup-<版本>.exe`。
- `dist/` 和 `release/` 必须保持在 `.gitignore`，不提交二进制产物。
- 不自动执行 `git push`、创建远程 release 或上传安装包；必须由用户明确授权。
- 若用户明确要求推送或发布到 GitHub，再单独核对目标仓库、tag、release notes 和安装包 hash。

## 结果报告

发版完成后简洁报告：版本、commit、完整测试结果、安装包绝对路径、大小、SHA256、签名状态、安装升级验证结果，以及任何未完成项。若构建失败，说明失败阶段和原始原因，不把 `dist\AIMux\AIMux.exe` 误报为最终单文件安装包。
