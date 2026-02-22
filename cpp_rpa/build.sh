#!/bin/bash

set -e

echo "=== 构建C++ RPA模块 (增强版) ==="

# 检查必要的依赖
echo "检查必要依赖..."
if ! command -v cmake &> /dev/null; then
    echo "❌ cmake 未安装，请先安装cmake"
    exit 1
fi

if ! command -v g++ &> /dev/null; then
    echo "❌ g++ 未安装，请先安装g++"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ python3 未安装，请先安装python3"
    exit 1
fi

# 检查pybind11是否可用
if ! python3 -c "import pybind11" &> /dev/null; then
    echo "⚠️ pybind11 未安装，尝试安装..."
    pip3 install pybind11
fi

# 创建构建目录
mkdir -p build
cd build

# 清理之前的构建
echo "清理之前的构建文件..."
make clean 2>/dev/null || true
rm -f wechat_rpa*.so 2>/dev/null || true

# 运行CMake配置
echo "运行CMake配置..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# 编译
echo "编译项目..."
make -j$(nproc)

# 检查编译结果
if [ $? -eq 0 ]; then
    echo "✅ 编译成功!"
    
    # 检查生成的Python绑定文件
    echo "检查生成的文件..."
    SO_FILE=$(ls wechat_rpa.cpython-*.so 2>/dev/null | head -n 1)
    if [ -n "$SO_FILE" ]; then
        echo "✅ 找到Python绑定文件: $SO_FILE"
        # 尝试导入测试
        echo "尝试Python导入测试..."
        cd ..
        if python3 -c "import sys; sys.path.insert(0, './build'); import wechat_rpa; print('✅ Python导入测试成功')"; then
            echo "✅ 模块可以正常导入"
        else
            echo "⚠️ 模块导入测试失败，但编译成功"
        fi
        
        echo ""
        echo "使用方法:"
        echo "1. 在Python中导入模块: import sys; sys.path.insert(0, './build'); import wechat_rpa"
        echo "2. 运行示例: PYTHONPATH=./build python3 examples/basic_usage.py"
        echo "3. 运行测试: PYTHONPATH=./build python3 test_compilation.py"
    else
        echo "❌ 未找到Python绑定文件，编译可能失败"
        cd ..
        exit 1
    fi
else
    echo "❌ 编译失败!"
    cd ..
    exit 1
fi

echo "=== 构建完成 ==="