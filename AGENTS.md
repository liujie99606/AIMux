# AIMux 项目规范

本文件适用于整个 AIMux 仓库。进行代码修改前，先根据改动范围阅读对应的 skill：

- 修改 `app/ui/` 下的 PySide6 桌面端视图、组件、弹窗、表格或交互时，阅读
  [`skills/aimux-frontend/SKILL.md`](skills/aimux-frontend/SKILL.md)。
- 修改 `app/` 下的 FastAPI 控制器、服务、DAO、模型、Schema、工具或 API/数据库业务时，阅读
  [`skills/aimux-backend/SKILL.md`](skills/aimux-backend/SKILL.md)。
- 修改 SQLModel 表结构、字段/约束/索引，或需要转换、回填已有持久化数据时，额外阅读
  [`skills/aimux-database-migrations/SKILL.md`](skills/aimux-database-migrations/SKILL.md)，并同步维护 `migrations/versions/`。普通 DAO/Service 增删改查、查询、排序和分页不需要新增 migration。
- 执行 Windows 打包、安装包生成、版本升级、正式发版、产物验证或排查发布脚本时，阅读
  [`skills/aimux-windows-release/SKILL.md`](skills/aimux-windows-release/SKILL.md)。
- 同时涉及多个范围时，对应 skill 都要阅读并遵守。

## 通用要求

- 保持现有目录分层和命名风格，避免无关重构。
- 每个 Python 文件首行使用 `from __future__ import annotations`，并补充完整类型注解。
- 修改后运行与影响范围匹配的聚焦测试；跨模块、共享基础设施、生命周期/全局配置改动或发布前再运行完整测试。完整测试命令为：

  ```powershell
  .\.venv\Scripts\python.exe -m pytest
  ```

- 改动完成且测试通过后，按项目约定创建中文说明的本地 git commit，不推送远程。

## 命令执行

如果 PowerShell 命令没有输出，改用：

`C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.4.0_x64__8wekyb3d8bbwe\pwsh.exe`
