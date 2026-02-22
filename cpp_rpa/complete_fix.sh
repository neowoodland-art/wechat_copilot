#!/bin/bash

echo "=== 开始修复C++ RPA模块 ==="

# 1. 备份并修复ATSPI引擎文件
echo "1. 修复ATSPI引擎文件..."
cp /home/neogh/wechat_copilot/cpp_rpa/src/atspi_engine.cpp /home/neogh/wechat_copilot/cpp_rpa/src/atspi_engine.cpp.backup
mv /home/neogh/wechat_copilot/cpp_rpa/src/atspi_engine_fixed.cpp /home/neogh/wechat_copilot/cpp_rpa/src/atspi_engine.cpp

# 2. 确保依赖已安装
echo "2. 检查并安装依赖..."
bash /home/neogh/wechat_copilot/cpp_rpa/install_deps.sh

# 3. 清理之前的构建
echo "3. 清理之前的构建文件..."
rm -rf /home/neogh/wechat_copilot/cpp_rpa/build

# 4. 重新构建
echo "4. 开始重新构建..."
cd /home/neogh/wechat_copilot/cpp_rpa

# 创建构建目录
mkdir -p build
cd build

# 运行CMake配置
echo "运行CMake配置..."
cmake ..

# 编译项目
echo "编译项目..."
make -j$(nproc)

# 检查编译结果
if [ $? -eq 0 ]; then
    echo "✅ 编译成功！"
    
    # 检查生成的库文件
    if [ -f "wechat_rpa.cpython-*.so" ]; then
        echo "✅ Python绑定库已生成"
        ls -la wechat_rpa.cpython-*.so
    else
        echo "⚠️  Python绑定库未找到，但编译过程已完成"
    fi
    
    echo ""
    echo "使用方法:"
    echo "1. 在Python中导入模块: import wechat_rpa"
    echo "2. 运行示例: python examples/basic_usage.py"
    echo "3. 运行测试: python test_atspi.py"
else
    echo "❌ 编译失败，请检查错误信息"
    exit 1
fi

echo "=== C++ RPA模块修复完成 ==="
