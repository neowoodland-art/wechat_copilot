#!/bin/bash

# 精确修复common.h中的RPAException定义
COMMON_H="/home/neogh/wechat_copilot/cpp_rpa/include/common.h"

if [ -f "$COMMON_H" ]; then
    # 备份原文件
    cp "$COMMON_H" "${COMMON_H}.backup_precise"
    
    # 完全重写RPAException类的定义
    sed -i '/class RPAException : public std::runtime_error {/,/};/c\
class RPAException : public std::runtime_error {\
public:\
    RPAException(ErrorCode code, const std::string& message)\
        : std::runtime_error(message), code_(code) {}\
    \
    ErrorCode code() const { return code_; }\
    \
private:\
    ErrorCode code_;\
};' "$COMMON_H"
    
    # 确保ELEMENT_NOT_FOUND错误码已添加
    if ! grep -q "ELEMENT_NOT_FOUND" "$COMMON_H"; then
        sed -i 's/INTERNAL_ERROR,/INTERNAL_ERROR,\n    ELEMENT_NOT_FOUND,/' "$COMMON_H"
    fi
    
    echo "✓ common.h文件已精确修复"
else
    echo "✗ 文件不存在: $COMMON_H"
fi
