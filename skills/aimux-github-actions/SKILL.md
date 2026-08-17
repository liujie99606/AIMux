---
name: aimux-github-actions
description: AIMux GitHub Actions 跨平台 Rust/Tauri 构建规范。配置、触发、查看或排查 Windows/macOS 构建和 GitHub Release 时使用。
---

# AIMux GitHub Actions

workflow 位于 `.github/workflows/build-release.yml`，构建 Windows x64/arm64 NSIS 安装包和 macOS x64/arm64 App ZIP。构建使用 Node.js、Rust stable、npm 和 Tauri CLI。

Windows/macOS 的每个架构都独立缓存 `src-tauri/target`、Cargo registry 和 Cargo git 依赖；首次构建仍需要完整编译，后续同一架构的构建会复用 Rust 增量产物。修改 `Cargo.lock`、Rust 工具链或切换架构时会产生新的缓存，这是预期行为。

## 构建触发

- 推送 `v*` tag 自动构建，并在全部平台成功后创建同名 GitHub Release。
- `workflow_dispatch` 只构建并上传 Actions Artifact，不自动创建正式 Release。
- 通过浏览器操作 GitHub Actions 前，确认当前浏览器已登录；遇到登录页时停止并提醒用户登录。

## 产物

- `AIMux-Windows-x64.exe`
- `AIMux-Windows-arm64.exe`
- `AIMux-macOS-x64.zip`
- `AIMux-macOS-arm64.zip`

workflow 不读取或上传用户数据目录中的数据库、配置和密钥。当前没有 Apple 公证、Windows 代码签名或自动更新服务，构建成功不等于获得系统信任。

## 排查顺序

1. 检查 workflow 使用的 runner 架构和 Tauri/Rust 工具链。
2. 检查 `npm ci`、`npm run build` 和 `npm run tauri build` 的原始日志。
3. 检查 `src-tauri/migrations`、图标和前端构建产物是否进入 bundle。
4. 检查上传路径和 Release tag 是否与矩阵架构一致。

不要替用户执行 `git push`、创建 tag 或上传外部发布物，除非用户明确要求。
