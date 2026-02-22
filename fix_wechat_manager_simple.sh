#!/bin/bash

echo "修复WeChatManager中的截图保存方法..."

WECHAT_MGR_CPP="/home/neogh/wechat_copilot/cpp_rpa/src/wechat_manager.cpp"
if [ -f "$WECHAT_MGR_CPP" ]; then
    # 备份原文件
    cp "$WECHAT_MGR_CPP" "${WECHAT_MGR_CPP}.backup_simple"
    
    # 用更简单的方式实现capture_and_save_message_area方法
    if ! grep -q "capture_and_save_message_area" "$WECHAT_MGR_CPP"; then
        # 在文件末尾添加方法实现
        cat >> "$WECHAT_MGR_CPP" << 'METHOD_IMPL'

bool WeChatManager::capture_and_save_message_area(const std::string& filepath) {
    // 确保微信激活
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    // 获取窗口信息
    WindowInfo window = get_wechat_window();
    
    // 计算消息区域（使用相对坐标计算）
    Region message_region;
    message_region.x = window.width / 4;           // 左侧留1/4
    message_region.y = window.height / 5;          // 顶部留1/5
    message_region.width = window.width * 3 / 4;    // 宽度占3/4
    message_region.height = window.height * 3 / 5;  // 高度占3/5
    
    // 截图整个窗口
    cv::Mat full_screenshot = capture_full_window();
    
    // 从全屏截图中裁剪消息区域
    cv::Rect roi(message_region.x, message_region.y, message_region.width, message_region.height);
    cv::Mat message_area_screenshot = full_screenshot(roi);
    
    // 保存到文件
    bool success = cv::imwrite(filepath, message_area_screenshot);
    
    if (!success) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "保存消息区域截图失败: " + filepath);
    }
    
    return success;
}
METHOD_IMPL
        
        echo "✓ 已添加简化的capture_and_save_message_area方法实现"
    else
        echo "ℹ️ capture_and_save_message_area方法已存在"
    fi
else
    echo "✗ 文件不存在: $WECHAT_MGR_CPP"
fi

echo ""
echo "修复完成！请重新运行构建脚本："
echo "cd /home/neogh/wechat_copilot/cpp_rpa"
echo "./build.sh"
