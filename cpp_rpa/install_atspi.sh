#!/bin/bash

# ATSPI依赖安装脚本
# 适用于Manjaro/Arch Linux

set -e

echo "=== 安装ATSPI依赖 ==="

# 更新包数据库
echo "更新包数据库..."
sudo pacman -Sy

# 安装ATSPI核心包
echo "安装ATSPI核心包..."
sudo pacman -S --needed at-spi2-core

# 安装Python绑定
echo "安装Python ATSPI绑定..."
# 尝试从官方仓库安装
if pacman -Si python-pyatspi &>/dev/null; then
    sudo pacman -S python-pyatspi
else
    echo "官方仓库中没有python-pyatspi，尝试从AUR安装..."
    if command -v yay &>/dev/null; then
        yay -S python-pyatspi
    else
        echo "请手动安装yay或使用pip安装: pip install pyatspi"
        pip install pyatspi
    fi
fi

# 安装其他依赖
echo "安装其他依赖..."
sudo pacman -S --needed \
    dbus \
    python-dbus \
    python-gobject \
    gtk3

# 启用服务
echo "启用ATSPI服务..."
# 检查是否在图形环境中
if [ -n "$DISPLAY" ]; then
    # 尝试启动ATSPI总线
    if ! pgrep -f "at-spi-bus-launcher" > /dev/null; then
        echo "启动ATSPI总线..."
        at-spi-bus-launcher &
        sleep 2
    fi
    
    # 尝试启动注册表
    if ! pgrep -f "at-spi2-registryd" > /dev/null; then
        echo "启动ATSPI注册表..."
        at-spi2-registryd &
        sleep 2
    fi
else
    echo "未检测到图形环境，跳过服务启动"
fi

# 配置X11权限
echo "配置X11权限..."
if [ -n "$DISPLAY" ]; then
    xhost +
fi

echo "=== 安装完成 ==="
echo "请运行 test_atspi.py 测试功能"