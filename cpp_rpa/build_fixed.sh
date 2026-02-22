#!/bin/bash
  
set -e

echo "=== 构建C++ RPA模块 (修正版) ==="

# 检查必要的依赖
echo "检查必要依赖..."
dependencies=("cmake" "g++" "python3" "pkg-config")
missing_deps=()

for dep in "${dependencies[@]}"; do
    if ! command -v "$dep" &> /dev/null; then
        missing_deps+=("$dep")
    fi
done

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "❌ 以下依赖未安装: ${missing_deps[*]}"
    echo "请先安装这些依赖后再运行此脚本"
    exit 1
fi

# 检查pybind11是否可用
if ! python3 -c "import pybind11" &> /dev/null; then
    echo "⚠️ pybind11 未安装，尝试安装..."
    pip3 install pybind11 || {
        echo "❌ pybind11安装失败"
        exit 1
    }
fi

# 清理之前的构建
echo "清理之前的构建文件..."
if [ -d "build" ]; then
    rm -rf build
fi

# 创建构建目录
mkdir -p build
cd build

# 运行CMake配置（启用详细输出）
echo "运行CMake配置..."
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_VERBOSE_MAKEFILE=ON

# 编译 - 使用单线程编译以获得更清晰的错误信息
echo "编译项目..."
make -j1 VERBOSE=1

# 检查编译结果
if [ $? -eq 0 ]; then
    echo "✅ 编译成功!"
    
    # 检查生成的Python绑定文件
    echo "检查生成的文件..."
    SO_FILES=$(ls wechat_rpa.cpython-*.so 2>/dev/null || echo "")
    if [ -n "$SO_FILES" ]; then
        echo "✅ 找到Python绑定文件: $SO_FILES"
        
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
        echo "3. 运行测试: PYTHONPATH=./build python3 test_atspi.py"
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
