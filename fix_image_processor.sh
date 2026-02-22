#!/bin/bash

echo "修复ImageProcessor类问题..."

# 在ImageProcessor头文件中添加方法声明
IMAGE_PROC_H="/home/neogh/wechat_copilot/cpp_rpa/include/image_processor.h"
if [ -f "$IMAGE_PROC_H" ]; then
    # 检查是否已经添加了声明
    if ! grep -q "capture_absolute_region" "$IMAGE_PROC_H"; then
        # 在capture_region方法后添加capture_absolute_region声明
        sed -i '/capture_region.*WindowInfo.*const Region&/a \
    cv::Mat capture_absolute_region(const Region& region);  // 截取绝对坐标区域' "$IMAGE_PROC_H"
        echo "✓ 已为ImageProcessor添加capture_absolute_region方法声明"
    fi
else
    echo "✗ 文件不存在: $IMAGE_PROC_H"
fi

# 在ImageProcessor实现文件中添加方法实现
IMAGE_PROC_CPP="/home/neogh/wechat_copilot/cpp_rpa/src/image_processor.cpp"
if [ -f "$IMAGE_PROC_CPP" ]; then
    # 检查是否已经添加了实现
    if ! grep -q "capture_absolute_region" "$IMAGE_PROC_CPP"; then
        # 在文件末尾类定义外添加方法实现
        cat >> "$IMAGE_PROC_CPP" << 'METHOD_IMPL'

cv::Mat ImageProcessor::capture_absolute_region(const Region& region) {
    // 使用maim截取指定绝对坐标区域
    std::string cmd = "maim -x " + std::to_string(region.x) + " -y " + std::to_string(region.y) + 
                     " -w " + std::to_string(region.width) + " -h " + std::to_string(region.height) + 
                     " /tmp/temp_capture_\$(date +%s)_\$\$.png";
    
    // 尝试执行截图命令
    int result = system(cmd.c_str());
    if (result != 0) {
        // 如果maim失败，尝试其他工具
        cmd = "scrot -o /tmp/temp_capture_\$(date +%s)_\$\$.png -a " + 
              std::to_string(region.x) + "," + std::to_string(region.y) + "," + 
              std::to_string(region.width) + "," + std::to_string(region.height);
        result = system(cmd.c_str());
        if (result != 0) {
            // 如果scrot也失败，抛出异常
            throw RPAException(ErrorCode::SCREENSHOT_FAILED, "截图失败，无法找到可用的截图工具");
        }
    }
    
    // 读取截图文件
    cv::Mat image = cv::imread("/tmp/temp_capture.png");
    if (image.empty()) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "无法读取截图文件");
    }
    
    return image;
}
METHOD_IMPL
        
        echo "✓ 已为ImageProcessor添加capture_absolute_region方法实现"
    fi
else
    echo "✗ 文件不存在: $IMAGE_PROC_CPP"
fi

echo ""
echo "修复完成！请重新运行构建脚本："
echo "cd /home/neogh/wechat_copilot/cpp_rpa"
echo "./build.sh"
