#!/bin/bash

# 编译和测试新功能脚本

set -e

echo "=== 编译和测试新功能 ==="

# 检查依赖
echo "检查依赖..."
if ! command -v cmake &> /dev/null; then
    echo "❌ cmake未安装"
    exit 1
fi

if ! command -v make &> /dev/null; then
    echo "❌ make未安装"
    exit 1
fi

# 安装ATSPI依赖
echo "安装ATSPI依赖..."
if [ -f "install_atspi.sh" ]; then
    chmod +x install_atspi.sh
    ./install_atspi.sh
else
    echo "⚠️ install_atspi.sh不存在，跳过ATSPI安装"
fi

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

# 测试基础功能
echo "测试基础功能..."
if [ -f "test_atspi.py" ]; then
    python3 test_atspi.py
else
    echo "⚠️ test_atspi.py不存在，跳过ATSPI测试"
fi

# 测试新功能
echo "测试新功能..."
if [ -f "test_new_features.py" ]; then
    python3 test_new_features.py
else
    echo "⚠️ test_new_features.py不存在，跳过新功能测试"
fi

# 测试Flask API
echo "测试Flask API..."
if [ -f "wechat_api_server.py" ]; then
    # 启动API服务器（后台）
    python3 wechat_api_server.py &
    API_PID=$!
    
    # 等待服务器启动
    sleep 3
    
    # 测试API状态
    if command -v curl &> /dev/null; then
        curl -s http://localhost:5000/api/status | python3 -m json.tool
    else
        echo "⚠️ curl未安装，跳过API测试"
    fi
    
    # 停止API服务器
    kill $API_PID 2>/dev/null || true
else
    echo "⚠️ wechat_api_server.py不存在，跳过Flask API测试"
fi

echo "=== 编译和测试完成 ==="

echo "\n=== 使用说明 ==="
echo "1. ATSPI功能测试: python3 test_atspi.py"
echo "2. 新功能测试: python3 test_new_features.py"
echo "3. Flask API服务器: python3 wechat_api_server.py"
echo "4. API文档: http://localhost:5000/api/status"
echo "\n注意：请确保微信已启动并处于可用状态"