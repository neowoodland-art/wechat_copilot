#!/bin/bash

# 简化capture_and_save_message_area的实现，避免使用不存在的方法
WECHAT_MGR_CPP="/home/neogh/wechat_copilot/cpp_rpa/src/wechat_manager.cpp"

if [ -f "$WECHAT_MGR_CPP" ]; then
    # 检查是否已经有该方法的实现，如果有则替换为简单版本
    if grep -q "capture_and_save_message_area" "$WECHAT_MGR_CPP"; then
        # 替换为简单的实现
        sed -i '/bool WeChatManager::capture_and_save_message_area/,/^}/d' "$WECHAT_MGR_CPP"
    fi
    
    # 添加简单的实现
    cat >> "$WECHAT_MGR_CPP" << 'METHOD_IMPL'

bool WeChatManager::capture_and_save_message_area(const std::string& filepath) {
    try {
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
        
        // 截图消息区域 - 使用现有方法
        cv::Mat screenshot = image_processor_.capture_region(window, message_region);
        
        // 保存到文件
        bool success = cv::imwrite(filepath, screenshot);
        
        if (!success) {
            throw RPAException(ErrorCode::SCREENSHOT_FAILED, "保存消息区域截图失败: " + filepath);
        }
        
        return success;
    } catch (const std::exception& e) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, std::string("截图保存失败: ") + e.what());
    }
}
METHOD_IMPL
    
    echo "✓ capture_and_save_message_area方法已添加（简化实现）"
else
    echo "✗ 文件不存在: $WECHAT_MGR_CPP"
fi
