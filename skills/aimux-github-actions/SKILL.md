---
name: aimux-github-actions
description: AIMux GitHub Actions 跨平台构建规范。用户要求配置、触发、查看或排查 GitHub Actions 的 Windows EXE/安装包、macOS APP/ZIP 构建，或通过浏览器操作 GitHub Actions 页面时使用。
---

# AIMux GitHub Actions

仓库 workflow 位于 `.github/workflows/build-release.yml`，构建 Windows 安装包和 macOS APP。支持 GitHub Actions 页面手动触发，也支持推送 `v*` tag 自动触发。

## 浏览器操作

1. 使用用户指定的浏览器打开：

   `https://github.com/liujie99606/AIMux/actions`

2. 检查是否已登录 GitHub。若出现登录页，停止操作并明确提醒用户在当前浏览器登录；用户回复已登录后继续，不要切换到其他浏览器或绕过登录。
3. 登录后检查 `Build Release Packages` workflow 是否存在、是否启用。
4. 需要立即构建时，点击 `Run workflow`，选择目标分支并确认运行。
5. 查看运行状态；完成后从 Artifacts 下载：

   - `AIMux-Windows-Installer`
   - `AIMux-macOS-App`

## Tag 构建与 Release

推送 `v*` tag 会自动触发构建。Windows 和 macOS 都成功后，workflow 会创建同名 GitHub Release，并上传两个平台产物。例如：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

不要替用户执行 `git push` 或创建 tag，除非用户明确要求。发布版本应先修改 `pyproject.toml` 的 `version`，确保标签使用对应的 `v<版本号>`，再提交代码和 tag。手动运行 workflow 只生成 Actions Artifact，不创建正式 Release。

## 产物边界

- Windows runner 使用 PyInstaller 和 Inno Setup，产出单文件 `AIMux-Setup-<版本>.exe`。
- macOS runner 使用 `scripts/mac_build.sh`，产出 `AIMux-macOS.zip`。
- `workflow_dispatch` 手动构建只上传 Artifact；`v*` 标签构建还会自动创建或更新 GitHub Release。
- workflow 不包含 Apple 签名、公证或 Windows 代码签名。
- 未签名产物可能触发 SmartScreen 或 Gatekeeper，不能将“构建成功”描述成“已获得系统信任”。
- workflow 不读取或上传 `%APPDATA%\aimux` 用户数据库、配置和密钥。
