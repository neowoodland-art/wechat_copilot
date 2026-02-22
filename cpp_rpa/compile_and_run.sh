#!/bin/bash

# 编译和运行脚本

set -e

echo "=== 编译和测试微信RPA ==="

# 清理旧构建
echo "清理旧构建..."
if [ -d "build" ]; then
    rm -rf build
fi

# 创建构建目录
echo "创建构建目录..."
mkdir -p build
cd build

# 配置CMake
echo "配置CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Debug

# 编译
echo "编译..."
make -j$(nproc)

# 返回上级目录
cd ..

echo "=== 编译完成 ==="

echo "\n=== 测试基础功能 ==="
if [ -f "test_without_atspi.py" ]; then
    python3 test_without_atspi.py
else
    echo "⚠️ test_without_atspi.py不存在，跳过测试"
fi

echo "\n=== 测试ATSPI功能 ==="
if [ -f "test_atspi.py" ]; then
    python3 test_atspi.py
else
    echo "⚠️ test_atspi.py不存在，跳过测试"
fi

echo "\n=== 完成 ==="