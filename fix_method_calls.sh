#!/bin/bash

# 修复WeChatManager.cpp中的方法调用
WECHAT_MGR_CPP="/home/neogh/wechat_copilot/cpp_rpa/src/wechat_manager.cpp"

if [ -f "$WECHAT_MGR_CPP" ]; then
    # 修复capture_specific_element方法中的错误
    sed -i 's/ELEMENT_NOT_FOUND/WINDOW_NOT_FOUND/g' "$WECHAT_MGR_CPP"
    
    # 修复ATSPI相关调用，使用现有方法
    sed -i 's/atspi_engine_.is_available()/atspi_engine_.initialize()/g' "$WECHAT_MGR_CPP"
    sed -i 's/atspi_engine_.find_all_controls_by_role(app, ATSPI_ROLE_PUSH_BUTTON)/atspi_engine_.find_controls_by_role(app, "push button")/g' "$WECHAT_MGR_CPP"
    sed -i 's/AtspiRect rect = atspi_engine_.get_control_bounds(buttons\[i\])/Region region = atspi_engine_.get_control_region(buttons\[i\])/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.x = rect.x/button_region.x = region.x/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.y = rect.y/button_region.y = region.y/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.width = rect.width/button_region.width = region.width/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.height = rect.height/button_region.height = region.height/g' "$WECHAT_MGR_CPP"
    
    # 对find_all_buttons方法也进行同样修复
    sed -i 's/atspi_engine_.find_all_controls_by_role(app, ATSPI_ROLE_PUSH_BUTTON)/atspi_engine_.find_controls_by_role(app, "push button")/g' "$WECHAT_MGR_CPP"
    sed -i 's/AtspiRect rect = atspi_engine_.get_control_bounds(btn)/Region region = atspi_engine_.get_control_region(btn)/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.x = rect.x/button_region.x = region.x/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.y = rect.y/button_region.y = region.y/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.width = rect.width/button_region.width = region.width/g' "$WECHAT_MGR_CPP"
    sed -i 's/button_region.height = rect.height/button_region.height = region.height/g' "$WECHAT_MGR_CPP"
    
    echo "✓ WeChatManager.cpp中的方法调用已修复"
else
    echo "✗ 文件不存在: $WECHAT_MGR_CPP"
fi
