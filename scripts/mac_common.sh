#!/usr/bin/env bash
set -euo pipefail

# macOS 启动与打包共用的 Python/虚拟环境引导函数。

_aimux_python_supports_project() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1
}


aimux_find_python() {
    # 优先寻找显式安装的新版 Python，避免误用 macOS 自带的旧 python3。
    local candidate
    local candidates=()

    if [ -n "${AIMUX_PYTHON:-}" ]; then
        candidates+=("$AIMUX_PYTHON")
    fi
    candidates+=(python3.14 python3.13 python3.12 python3)

    for candidate in "${candidates[@]}"; do
        if ! command -v "$candidate" >/dev/null 2>&1; then
            continue
        fi
        if _aimux_python_supports_project "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done

    echo "[AIMux] 未找到 Python 3.12 或更新版本。" >&2
    echo "[AIMux] 请先安装新版 Python 后重新运行：" >&2
    if command -v brew >/dev/null 2>&1; then
        echo "  brew install python@3.13" >&2
    else
        echo "  通过 https://www.python.org/downloads/macos/ 安装 Python 3.12+" >&2
        echo "  或安装 Homebrew 后执行：brew install python@3.13" >&2
    fi
    echo "[AIMux] 也可指定解释器：AIMUX_PYTHON=/完整路径/python3.13 ./scripts/mac_start.sh" >&2
    return 1
}


aimux_ensure_venv() {
    # 创建兼容的虚拟环境，并按调用方需要同步依赖。
    local dependency_spec="$1"
    local python

    if [ -x ".venv/bin/python" ]; then
        if ! _aimux_python_supports_project ".venv/bin/python"; then
            echo "[AIMux] 现有 .venv 使用的 Python 版本低于 3.12。" >&2
            echo "[AIMux] 安装新版 Python 后执行 rm -rf .venv，再重新运行本脚本。" >&2
            return 1
        fi
    else
        python="$(aimux_find_python)"
        echo "[AIMux] 使用 $($python --version) 创建 .venv ..."
        "$python" -m venv .venv
        .venv/bin/python -m pip install --upgrade pip
    fi

    echo "[AIMux] 正在同步依赖 ..."
    .venv/bin/python -m pip install -e "$dependency_spec"
}
