#!/usr/bin/env bash
set -euo pipefail

# AIMux macOS 打包脚本：自动创建虚拟环境、安装依赖并打包为桌面应用。

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "[AIMux] 未检测到虚拟环境，正在创建 .venv ..."
    python3 -m venv .venv
    echo "[AIMux] 正在安装依赖 ..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e ".[dev]"
fi

echo "[AIMux] 正在打包，首次构建需要下载依赖，请耐心等待 ..."
.venv/bin/python scripts/build.py

echo ""
echo "[AIMux] 打包完成！应用位于：dist/AIMux/AIMux.app"
