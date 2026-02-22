#!/bin/bash

# 基础功能编译脚本（不包含ATSPI）

set -e

echo "=== 编译基础功能C++ RPA模块 ==="

# 清理旧构建
echo "清理旧构建..."
if [ -d "build" ]; then
    rm -rf build
fi

# 创建构建目录
echo "创建构建目录..."
mkdir -p build
cd build

# 运行CMake
echo "运行CMake配置..."
cmake .. -DCMAKE_BUILD_TYPE=Debug -DATSPI_FOUND=OFF

# 编译
echo "编译项目..."
make -j$(nproc)

# 返回上级目录
cd ..

echo "=== 编译完成 ==="
echo "现在可以运行测试脚本了"
echo "1. 测试基础功能: python3 test_without_atspi.py"
echo "2. 测试拟人化功能: python3 test_basic_functionality.py"