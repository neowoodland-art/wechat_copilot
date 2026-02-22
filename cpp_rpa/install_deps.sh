#!/bin/bash

set -e

echo "=== 安装C++ RPA模块依赖 ==="

# 检测操作系统类型
if [ -f "/etc/arch-release" ]; then
    echo "检测到Arch/Manjaro系统"
    
    # 更新系统
    echo "更新系统..."
    sudo pacman -Syu --noconfirm
    
    # 安装基础依赖
    echo "安装基础依赖..."
    sudo pacman -S --noconfirm base-devel cmake
    
    # 安装OpenCV
    echo "安装OpenCV..."
    sudo pacman -S --noconfirm opencv
    
    # 安装Tesseract和Leptonica
    echo "安装Tesseract和Leptonica..."
    sudo pacman -S --noconfirm tesseract tesseract-data-chi_sim leptonica
    
    # 安装Python相关依赖
    echo "安装Python相关依赖..."
    # 安装pybind11（如果在官方仓库中）
    sudo pacman -S --noconfirm python-opencv
    
    # 检查是否有pybind11包
    if pacman -Ss pybind11 | grep -q "pybind11"; then
        sudo pacman -S --noconfirm pybind11
    elif pacman -Ss python-pybind11 | grep -q "python-pybind11"; then
        sudo pacman -S --noconfirm python-pybind11
    else
        # 如果官方仓库中没有，使用yay安装AUR包
        echo "在AUR中搜索pybind11..."
        yay -S --noconfirm python-pybind11
    fi
    
    # 安装窗口管理和截图工具
    echo "安装窗口管理和截图工具..."
    sudo pacman -S --noconfirm xdotool wmctrl maim
    
    echo "=== 依赖安装完成 (Arch/Manjaro) ==="
    
elif [ -f "/etc/debian_version" ]; then
    echo "检测到Debian/Ubuntu系统"
    
    # 更新系统
    echo "更新系统..."
    sudo apt update
    sudo apt upgrade -y
    
    # 安装基础依赖
    echo "安装基础依赖..."
    sudo apt install -y build-essential cmake
    
    # 安装OpenCV
    echo "安装OpenCV..."
    sudo apt install -y libopencv-dev
    
    # 安装Tesseract和Leptonica
    echo "安装Tesseract和Leptonica..."
    sudo apt install -y tesseract-ocr libtesseract-dev libleptonica-dev tesseract-ocr-chi-sim
    
    # 安装Python相关依赖
    echo "安装Python相关依赖..."
    sudo apt install -y python3-dev python3-pip
    pip3 install pybind11 opencv-python
    
    # 安装窗口管理和截图工具
    echo "安装窗口管理和截图工具..."
    sudo apt install -y xdotool wmctrl maim
    
    echo "=== 依赖安装完成 (Debian/Ubuntu) ==="
    
else
    echo "警告: 无法检测操作系统类型"
    echo "请手动安装以下依赖:"
    echo "1. 基础依赖: build-essential, cmake"
    echo "2. OpenCV"
    echo "3. Tesseract (含中文语言包) 和 Leptonica"
    echo "4. Python相关: pybind11"
    echo "5. 窗口管理和截图工具: xdotool, wmctrl, maim"
    
    echo "=== 依赖安装脚本完成 ==="
    exit 1
fi

# 验证安装
echo "验证依赖安装..."

# 验证cmake
if command -v cmake &> /dev/null; then
    echo "✅ cmake已安装"
else
    echo "❌ cmake未安装"
fi

# 验证g++
if command -v g++ &> /dev/null; then
    echo "✅ g++已安装"
else
    echo "❌ g++未安装"
fi

# 验证OpenCV
if pkg-config --exists opencv4 || pkg-config --exists opencv; then
    echo "✅ OpenCV已安装"
else
    echo "❌ OpenCV未安装"
fi

# 验证Tesseract
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract已安装"
else
    echo "❌ Tesseract未安装"
fi

# 验证xdotool
if command -v xdotool &> /dev/null; then
    echo "✅ xdotool已安装"
else
    echo "❌ xdotool未安装"
fi

# 验证maim
if command -v maim &> /dev/null; then
    echo "✅ maim已安装"
else
    echo "❌ maim未安装"
fi

echo "=== 依赖验证完成 ==="
echo "现在可以运行 ./build.sh 来编译C++ RPA模块"
