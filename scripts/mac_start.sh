#!/usr/bin/env bash
set -euo pipefail

# AIMux macOS 启动脚本：自动选择 Python 3.12+、创建虚拟环境并启动桌面端。

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/mac_common.sh"
cd "$script_dir/.."

aimux_ensure_venv "."

echo "[AIMux] 正在启动 ..."
exec .venv/bin/python -m app
