#!/usr/bin/env bash
set -euo pipefail

# AIMux macOS 打包脚本：自动选择 Python 3.12+、创建虚拟环境并打包桌面应用。

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/mac_common.sh"
cd "$script_dir/.."

aimux_ensure_venv ".[dev]"

echo "[AIMux] 正在打包，首次构建需要下载依赖，请耐心等待 ..."
.venv/bin/python scripts/build.py

echo ""
echo "[AIMux] 打包完成！应用位于：dist/AIMux/AIMux.app"
