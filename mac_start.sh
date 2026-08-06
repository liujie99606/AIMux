#!/usr/bin/env bash
set -euo pipefail

# AIMux macOS 启动脚本：自动创建虚拟环境、安装依赖并启动桌面端。

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "[AIMux] 未检测到虚拟环境，正在创建 .venv ..."
    python3 -m venv .venv
    echo "[AIMux] 正在安装依赖 ..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e ".[dev]"
fi

echo "[AIMux] 正在启动 ..."
exec .venv/bin/python -m app
