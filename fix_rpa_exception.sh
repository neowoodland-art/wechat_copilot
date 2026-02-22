#!/bin/bash

echo "修复RPAException构造函数问题..."

# 修复RPAException类定义
COMMON_H="/home/neogh/wechat_copilot/cpp_rpa/include/common.h"
if [ -f "$COMMON_H" ]; then
    # 备份原文件
    cp "$COMMON_H" "${COMMON_H}.backup_exception"
    
    # 确保RPAException类有正确的构造函数定义
    awk '
    /class RPAException : public std::runtime_error {/ {
        print $0
        print "public:"
        print "    RPAException(ErrorCode code, const std::string& message)"
        print "        : std::runtime_error(message), code_(code) {}"
        print "    "
        next
    }
    /ErrorCode code\(\) const/ {
        print "private:"
        print "    ErrorCode code_;"
        print "    "
        print $0
        next
    }
    { print $0 }
    ' "${COMMON_H}.backup_exception" > "$COMMON_H"
    
    echo "✓ 已修复RPAException类定义"
else
    echo "✗ 文件不存在: $COMMON_H"
fi

# 删除之前可能添加的错误实现
WECHAT_MGR_CPP="/home/neogh/wechat_copilot/cpp_rpa/src/wechat_manager.cpp"
if [ -f "$WECHAT_MGR_CPP" ]; then
    # 删除之前可能添加的capture_absolute_region方法实现
    sed -i '/cv::Mat ImageProcessor::capture_absolute_region/,/^}/d' "$WECHAT_MGR_CPP"
fi

echo ""
echo "修复完成！请重新运行构建脚本："
echo "cd /home/neogh/wechat_copilot/cpp_rpa"
echo "./build.sh"
