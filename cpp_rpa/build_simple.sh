#!/bin/bash

# 简化编译脚本，不包含ATSPI功能

set -e

echo "=== 简化编译C++ RPA模块（不包含ATSPI） ==="

# 清理旧构建
if [ -d "build" ]; then
    rm -rf build
fi

# 创建构建目录
mkdir -p build
cd build

# 配置CMake（禁用ATSPI）
echo "配置CMake（禁用ATSPI）..."
cmake .. -DCMAKE_BUILD_TYPE=Debug -DATSPI_FOUND=OFF

# 编译
echo "编译..."
make -j$(nproc)

# 返回上级目录
cd ..

echo "=== 编译完成 ==="
echo "注意：ATSPI功能已禁用，将使用xdotool作为输入模拟方案"