#!/bin/bash

# 安装ydotool脚本
# ydotool使用Linux内核的uinput框架，比xdotool更底层

set -e

echo "=== 安装ydotool ==="

# 检查是否已安装
if command -v ydotool &> /dev/null; then
    echo "✅ ydotool已安装"
    ydotool --version
else
    echo "安装ydotool..."
    
    # 尝试从包管理器安装
    if command -v pacman &> /dev/null; then
        # Arch Linux
        sudo pacman -S --needed git cmake
        git clone https://github.com/ReimuNotMoe/ydotool.git
        cd ydotool
        mkdir build
        cd build
        cmake ..
        make -j$(nproc)
        sudo make install
        cd ../..
        rm -rf ydotool
    elif command -v apt &> /dev/null; then
        # Debian/Ubuntu
        sudo apt update
        sudo apt install -y git cmake
        git clone https://github.com/ReimuNotMoe/ydotool.git
        cd ydotool
        mkdir build
        cd build
        cmake ..
        make -j$(nproc)
        sudo make install
        cd ../..
        rm -rf ydotool
    else
        echo "❌ 不支持的包管理器，请手动安装ydotool"
        exit 1
    fi
    
    echo "✅ ydotool安装完成"
fi

# 检查uinput模块
if ! lsmod | grep -q uinput; then
    echo "加载uinput模块..."
    sudo modprobe uinput
    echo "uinput" | sudo tee -a /etc/modules
fi

# 检查权限
if [ ! -w /dev/uinput ]; then
    echo "设置uinput设备权限..."
    sudo chmod 666 /dev/uinput
    echo "KERNEL==\"uinput\", MODE=\"0666\"" | sudo tee /etc/udev/rules.d/99-uinput.rules
    sudo udevadm control --reload-rules
fi

echo "✅ ydotool配置完成"

# 测试ydotool
echo "测试ydotool..."
ydotool --version

echo "✅ ydotool安装和配置完成！"