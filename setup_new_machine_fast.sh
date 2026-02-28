#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WITH_SYSTEM_DEPS=0
SKIP_PYTHON=0
SKIP_FRONTEND=0
SKIP_CPP=0
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_INDEX_URL="${PIP_INDEX_URL:-}"
NPM_REGISTRY="${NPM_REGISTRY:-}"

usage() {
  cat <<EOF
用法: ./setup_new_machine_fast.sh [选项]

选项:
  --with-system-deps      安装系统依赖(apt)
  --skip-python           跳过 Python 虚拟环境重建
  --skip-frontend         跳过前端依赖安装
  --skip-cpp              跳过 C++ RPA 构建
  --python-bin BIN        指定 Python 解释器(如 python3.11)
  --pip-index-url URL     指定 pip 镜像源
  --npm-registry URL      指定 npm 镜像源
  -h, --help              显示帮助

示例:
  ./setup_new_machine_fast.sh
  ./setup_new_machine_fast.sh --with-system-deps
  ./setup_new_machine_fast.sh --pip-index-url https://pypi.tuna.tsinghua.edu.cn/simple --npm-registry https://registry.npmmirror.com
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-system-deps)
      WITH_SYSTEM_DEPS=1
      shift
      ;;
    --skip-python)
      SKIP_PYTHON=1
      shift
      ;;
    --skip-frontend)
      SKIP_FRONTEND=1
      shift
      ;;
    --skip-cpp)
      SKIP_CPP=1
      shift
      ;;
    --python-bin)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --pip-index-url)
      PIP_INDEX_URL="$2"
      shift 2
      ;;
    --npm-registry)
      NPM_REGISTRY="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      usage
      exit 1
      ;;
  esac
done

echo "== WeChat Copilot 新机器快速初始化 =="
echo "项目目录: ${ROOT_DIR}"

if [[ ${WITH_SYSTEM_DEPS} -eq 1 ]]; then
  if ! command -v apt >/dev/null 2>&1; then
    echo "❌ 当前系统不支持 apt，无法自动安装系统依赖"
    exit 1
  fi
  echo "📦 安装系统依赖..."
  sudo apt update
  sudo apt install -y build-essential cmake \
    libopencv-dev libleptonica-dev libtesseract-dev tesseract-ocr tesseract-ocr-chi-sim \
    python3-dev python3-pip xdotool wmctrl maim libatspi2.0-dev pkg-config
fi

if [[ ${SKIP_PYTHON} -eq 0 ]]; then
  echo "🐍 重建 Python 虚拟环境..."
  PIP_INDEX_URL="${PIP_INDEX_URL}" PYTHON_BIN="${PYTHON_BIN}" "${ROOT_DIR}/rebuild_venv_fast.sh"
else
  echo "⏭️ 跳过 Python 虚拟环境"
fi

if [[ ${SKIP_FRONTEND} -eq 0 ]]; then
  echo "🧩 安装前端依赖..."
  if ! command -v npm >/dev/null 2>&1; then
    echo "❌ 未找到 npm，请先安装 Node.js 16+ 与 npm"
    exit 1
  fi

  pushd "${ROOT_DIR}/frontend" >/dev/null
  if [[ -f package-lock.json ]]; then
    if [[ -n "${NPM_REGISTRY}" ]]; then
      npm ci --registry "${NPM_REGISTRY}"
    else
      npm ci
    fi
  else
    if [[ -n "${NPM_REGISTRY}" ]]; then
      npm install --registry "${NPM_REGISTRY}"
    else
      npm install
    fi
  fi
  popd >/dev/null
else
  echo "⏭️ 跳过前端依赖安装"
fi

if [[ ${SKIP_CPP} -eq 0 ]]; then
  echo "🛠️ 构建 C++ RPA 模块..."
  if [[ -d "${ROOT_DIR}/cpp_rpa" ]]; then
    pushd "${ROOT_DIR}/cpp_rpa" >/dev/null
    ./build.sh
    popd >/dev/null
  else
    echo "❌ 未找到 cpp_rpa 目录"
    exit 1
  fi
else
  echo "⏭️ 跳过 C++ 构建"
fi

echo ""
echo "✅ 初始化完成"
echo "后端启动: source ${ROOT_DIR}/.venv/bin/activate && cd ${ROOT_DIR}/backend && uvicorn main:app --host 0.0.0.0 --port 8000"
echo "前端启动: cd ${ROOT_DIR}/frontend && npm run dev"
