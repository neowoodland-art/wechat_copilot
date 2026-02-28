#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
REQ_FILE="${ROOT_DIR}/backend/requirements.txt"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_INDEX_URL="${PIP_INDEX_URL:-}"

if [[ ! -f "${REQ_FILE}" ]]; then
  echo "❌ 找不到依赖文件: ${REQ_FILE}"
  exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "❌ 未找到 Python: ${PYTHON_BIN}"
  echo "请先安装 Python 3.11+，或执行: PYTHON_BIN=python3.11 ./rebuild_venv_fast.sh"
  exit 1
fi

echo "🚀 开始重建虚拟环境: ${VENV_DIR}"
rm -rf "${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "⬆️ 升级基础打包工具"
python -m pip install -U pip setuptools wheel

EXTRA_PIP_ARGS=()
if [[ -n "${PIP_INDEX_URL}" ]]; then
  EXTRA_PIP_ARGS+=("-i" "${PIP_INDEX_URL}")
  echo "🌐 使用镜像源: ${PIP_INDEX_URL}"
fi

if command -v uv >/dev/null 2>&1; then
  echo "⚡ 检测到 uv，使用 uv pip 加速安装"
  uv pip install --python "${VENV_DIR}/bin/python" -r "${REQ_FILE}" "${EXTRA_PIP_ARGS[@]}"
else
  echo "📦 使用 pip 安装依赖"
  python -m pip install -r "${REQ_FILE}" "${EXTRA_PIP_ARGS[@]}"
fi

echo "✅ 虚拟环境重建完成"
echo "使用方式: source ${VENV_DIR}/bin/activate"
