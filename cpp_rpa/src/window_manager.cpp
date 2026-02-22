#include "window_manager.h"
#include <iostream>
#include <sstream>
#include <cstring>
#include <sys/wait.h>
#include <unistd.h>

// 临时关闭调试输出
#define DEBUG_PRINT(msg)

namespace wechat_rpa {

WindowManager::WindowManager() {
    // 初始化微信窗口名称列表
    wechat_window_names_ = WECHAT_WINDOW_NAMES;
    // 设置默认超时时间
    activation_timeout_ = 10000; // 10秒
    // 设置最大重试次数
    max_retry_count_ = 3;
    // 不在构造函数中刷新窗口缓存，避免卡住
    // refresh_window_cache();
}

bool WindowManager::is_command_available(const std::string& command) const {
    std::string cmd = "which " + command + " >/dev/null 2>&1";
    int result = system(cmd.c_str());
    return result == 0;
}

bool WindowManager::is_ydotool_available() const {
    // 检查ydotool是否可用
    return is_command_available("ydotool");
}

std::string WindowManager::execute_mouse_command(int x, int y) const {
    // 暂时强制使用xdotool，因为ydotool有问题
    bool use_xdotool = true;
    DEBUG_PRINT("强制使用xdotool: " << std::boolalpha << use_xdotool);
    
    if (use_xdotool) {
        // xdotool使用绝对坐标
        std::string cmd = "xdotool mousemove " + std::to_string(x) + " " + std::to_string(y);
        DEBUG_PRINT("执行命令: " << cmd);
        return execute_command(cmd, 500);
    } else {
        // ydotool使用相对坐标
        std::string cmd = "ydotool mousemove " + std::to_string(x) + " " + std::to_string(y);
        DEBUG_PRINT("执行命令: " << cmd);
        return execute_command(cmd, 500);
    }
}

std::string WindowManager::execute_click_command(int button) const {
    // 暂时强制使用xdotool，因为ydotool有问题
    std::string cmd = "xdotool click " + std::to_string(button);
    DEBUG_PRINT("执行命令: " << cmd);
    return execute_command(cmd, 500);
}

std::string WindowManager::execute_command(const std::string& command, int timeout_ms) const {
    DEBUG_PRINT("执行命令: " + command);
    
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) {
        DEBUG_PRINT("无法打开管道执行命令: " + command);
        throw RPAException(ErrorCode::INTERNAL_ERROR, "无法执行命令: " + command);
    }
    
    char buffer[128];
    std::string result;
    
    // 简单实现：直接读取，使用fgets的阻塞特性
    // 如果命令真的卡住，用户可以通过Ctrl+C中断
    DEBUG_PRINT("开始读取命令输出");
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        result += buffer;
    }
    DEBUG_PRINT("命令输出长度: " + std::to_string(result.length()));
    
    int exit_code = pclose(pipe);
    DEBUG_PRINT("pclose返回码: " + std::to_string(exit_code));
    
    // 检查命令是否正常退出
    if (WIFEXITED(exit_code)) {
        int status = WEXITSTATUS(exit_code);
        DEBUG_PRINT("命令退出状态: " + std::to_string(status));
        if (status != 0) {
            DEBUG_PRINT("命令执行失败，状态码: " + std::to_string(status));
            throw RPAException(ErrorCode::INTERNAL_ERROR, "命令执行失败: " + command);
        }
    } else {
        // 命令异常退出
        DEBUG_PRINT("命令异常退出");
        throw RPAException(ErrorCode::INTERNAL_ERROR, "命令异常退出: " + command);
    }
    
    DEBUG_PRINT("命令执行成功");
    return result;
}

bool WindowManager::activate_with_xdotool(const std::string& window_id) const {
    if (!is_command_available("xdotool")) {
        return false;
    }
    
    std::string cmd = "xdotool windowactivate --sync " + window_id;
    try {
        std::string result = execute_command(cmd, activation_timeout_);
        return true;
    } catch (const RPAException& e) {
        std::cerr << "xdotool激活失败: " << e.what() << std::endl;
        return false;
    }
}

bool WindowManager::activate_with_wmctrl(const std::string& window_name) const {
    if (!is_command_available("wmctrl")) {
        return false;
    }
    
    std::string cmd = "wmctrl -a \"" + window_name + "\"";
    try {
        std::string result = execute_command(cmd, activation_timeout_);
        return true;
    } catch (const RPAException& e) {
        std::cerr << "wmctrl激活失败: " << e.what() << std::endl;
        return false;
    }
}

bool WindowManager::activate_with_enlightenment(const std::string& window_name) const {
    if (!is_command_available("enlightenment_remote")) {
        return false;
    }
    
    std::string cmd = "enlightenment_remote -raise \"" + window_name + "\"";
    try {
        std::string result = execute_command(cmd, activation_timeout_);
        return true;
    } catch (const RPAException& e) {
        std::cerr << "enlightenment_remote激活失败: " << e.what() << std::endl;
        return false;
    }
}

WindowInfo WindowManager::parse_window_geometry(const std::string& window_id, const std::string& title) {
    WindowInfo info;
    info.id = window_id;
    info.title = title;
    
    // 使用xdotool获取窗口几何信息
    if (is_command_available("xdotool")) {
        try {
            std::string cmd = "xdotool getwindowgeometry " + window_id;
            std::string result = execute_command(cmd);
            
            // 解析输出
            std::istringstream iss(result);
            std::string line;
            
            while (std::getline(iss, line)) {
                if (line.find("Position:") != std::string::npos) {
                    // 解析位置
                    size_t pos = line.find(":");
                    if (pos != std::string::npos) {
                        std::string pos_str = line.substr(pos + 1);
                        size_t comma_pos = pos_str.find(",");
                        if (comma_pos != std::string::npos) {
                            info.x = std::stoi(pos_str.substr(0, comma_pos));
                            // 提取y坐标，去除可能的屏幕信息
                            std::string y_str = pos_str.substr(comma_pos + 1);
                            size_t screen_pos = y_str.find("(");
                            if (screen_pos != std::string::npos) {
                                y_str = y_str.substr(0, screen_pos);
                            }
                            info.y = std::stoi(y_str);
                        }
                    }
                } else if (line.find("Geometry:") != std::string::npos) {
                    // 解析几何尺寸
                    size_t pos = line.find(":");
                    if (pos != std::string::npos) {
                        std::string geo_str = line.substr(pos + 1);
                        size_t x_pos = geo_str.find("x");
                        if (x_pos != std::string::npos) {
                            info.width = std::stoi(geo_str.substr(0, x_pos));
                            info.height = std::stoi(geo_str.substr(x_pos + 1));
                        }
                    }
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "解析窗口几何信息失败: " << e.what() << std::endl;
        }
    }
    
    // 检查是否获取到有效信息
    if (info.width == 0 || info.height == 0) {
        // 默认值
        info.x = 0;
        info.y = 0;
        info.width = 800;
        info.height = 600;
    }
    
    // 不在这里检查激活状态，避免无限循环
    // info.is_active = is_window_active(info);
    info.is_active = false;  // 默认为false，由调用者检查
    
    return info;
}

WindowInfo WindowManager::find_wechat_window() {
    std::vector<WindowInfo> all_wechat_windows;
    
    // 遍历所有可能的微信窗口名称
    for (const std::string& name : wechat_window_names_) {
        try {
            std::vector<WindowInfo> windows = search_windows(name);
            all_wechat_windows.insert(all_wechat_windows.end(), windows.begin(), windows.end());
        } catch (const RPAException& e) {
            // 忽略搜索错误，继续尝试下一个名称
            std::cerr << "搜索窗口 '" << name << "' 失败: " << e.what() << std::endl;
        }
    }
    
    if (all_wechat_windows.empty()) {
        // 未找到微信窗口，尝试点击任务栏图标启动
        try_launch_wechat_from_tray();
        throw RPAException(ErrorCode::WINDOW_NOT_FOUND, "未找到微信窗口");
    }
    
    // 按优先级排序窗口
    WindowInfo best_window;
    bool found = false;
    
    // 优先级1: 有WM_CLASS("wechat")且尺寸较大的窗口
    for (const WindowInfo& window : all_wechat_windows) {
        try {
            std::string cmd = "xprop -id " + window.id + " WM_CLASS";
            std::string result = execute_command(cmd, 2000); // 2秒超时
            if (result.find("wechat") != std::string::npos && 
                window.width > 500 && window.height > 500) {
                if (!found || window.width * window.height > best_window.width * best_window.height) {
                    best_window = window;
                    found = true;
                }
            }
        } catch (const RPAException& e) {
            // 忽略错误，继续检查下一个窗口
        }
    }
    
    // 优先级2: 没有WM_CLASS但尺寸较大的窗口
    if (!found) {
        for (const WindowInfo& window : all_wechat_windows) {
            if (window.width > 500 && window.height > 500) {
                if (!found || window.width * window.height > best_window.width * best_window.height) {
                    best_window = window;
                    found = true;
                }
            }
        }
    }
    
    // 优先级3: 任何窗口
    if (!found && !all_wechat_windows.empty()) {
        best_window = all_wechat_windows[0];
        found = true;
    }
    
    if (found) {
        return best_window;
    }
    
    throw RPAException(ErrorCode::WINDOW_NOT_FOUND, "未找到合适的微信窗口");
}

void WindowManager::try_launch_wechat_from_tray() {
    // 查找任务栏窗口
    std::string cmd = "xdotool search --name 'WeChatAppEx'";
    try {
        std::string result = execute_command(cmd);
        if (!result.empty()) {
            // 尝试点击第一个任务栏窗口
            std::istringstream iss(result);
            std::string window_id;
            if (iss >> window_id) {
                execute_command("xdotool click --window " + window_id + " 1", 1000);
            }
        }
    } catch (const RPAException& e) {
        // 忽略错误
    }
}

bool WindowManager::activate_window(const WindowInfo& window) {
    // 检查窗口是否已经激活
    if (is_window_active(window)) {
        return true;
    }
    
    // 尝试多种激活方法
    bool activated = false;
    
    // 方法1: 使用wmctrl激活（通常更可靠）
    activated = activate_with_wmctrl(window.title);
    if (activated) {
        return true;
    }
    
    // 方法2: 使用xdotool激活（不使用--sync）
    activated = activate_with_xdotool(window.id);
    if (activated) {
        return true;
    }
    
    // 方法3: 使用enlightenment_remote激活
    activated = activate_with_enlightenment(window.title);
    if (activated) {
        return true;
    }
    
    // 所有方法都失败
    return false;
}

bool WindowManager::ensure_wechat_active() {
    try {
        // 查找微信窗口
        WindowInfo window = find_wechat_window();
        
        // 检查窗口是否最小化
        bool is_minimized = false;
        std::string cmd = "xprop -id " + window.id + " _NET_WM_STATE";
        try {
            std::string result = execute_command(cmd);
            if (result.find("_NET_WM_STATE_HIDDEN") != std::string::npos) {
                is_minimized = true;
            }
        } catch (const RPAException& e) {
            // 忽略错误
        }
        
        // 如果窗口最小化，先尝试恢复
        if (is_minimized) {
            cmd = "xdotool windowmap " + window.id;
            try {
                execute_command(cmd, 1000);
                usleep(200000); // 等待200ms
            } catch (const RPAException& e) {
                // 忽略错误
            }
        }
        
        // 尝试激活窗口
        bool activated = activate_window(window);
        if (!activated) {
            // 重试
            for (int i = 0; i < max_retry_count_; ++i) {
                activated = activate_window(window);
                if (activated) {
                    break;
                }
                // 等待一段时间后重试
                usleep(500000); // 500ms
            }
        }
        
        return activated;
    } catch (const RPAException& e) {
        std::cerr << "确保微信激活失败: " << e.what() << std::endl;
        return false;
    }
}

bool WindowManager::is_window_active(const WindowInfo& window) {
    try {
        // 获取活动窗口
        WindowInfo active_window = get_active_window();
        // 检查是否为同一个窗口
        return active_window.id == window.id;
    } catch (const RPAException& e) {
        std::cerr << "检查窗口激活状态失败: " << e.what() << std::endl;
        return false;
    }
}

WindowInfo WindowManager::get_window_info(const std::string& window_id) {
    // 检查缓存
    { 
        std::lock_guard<std::mutex> lock(cache_mutex_);
        auto it = window_cache_.find(window_id);
        if (it != window_cache_.end()) {
            return it->second;
        }
    }
    
    // 缓存中没有，获取新信息
    WindowInfo info;
    info.id = window_id;
    
    // 使用xdotool获取窗口标题
    if (is_command_available("xdotool")) {
        try {
            std::string cmd = "xdotool getwindowname " + window_id;
            std::string title = execute_command(cmd);
            // 去除换行符
            if (!title.empty() && title.back() == '\n') {
                title.pop_back();
            }
            info.title = title;
        } catch (const RPAException& e) {
            std::cerr << "获取窗口标题失败: " << e.what() << std::endl;
            info.title = "";
        }
    }
    
    // 解析窗口几何信息
    info = parse_window_geometry(window_id, info.title);
    
    // 更新缓存
    { 
        std::lock_guard<std::mutex> lock(cache_mutex_);
        window_cache_[window_id] = info;
    }
    
    return info;
}

std::vector<WindowInfo> WindowManager::search_windows(const std::string& window_name) {
    std::vector<WindowInfo> windows;
    
    // 使用xdotool搜索窗口
    if (is_command_available("xdotool")) {
        try {
            std::string cmd = "xdotool search --name \"" + window_name + "\"";
            std::string result = execute_command(cmd);
            
            // 解析结果
            std::istringstream iss(result);
            std::string window_id;
            
            while (iss >> window_id) {
                try {
                    WindowInfo info = get_window_info(window_id);
                    windows.push_back(info);
                } catch (const RPAException& e) {
                    std::cerr << "获取窗口信息失败: " << e.what() << std::endl;
                }
            }
        } catch (const RPAException& e) {
            std::cerr << "搜索窗口失败: " << e.what() << std::endl;
        }
    }
    
    return windows;
}

WindowInfo WindowManager::get_active_window() {
    // 使用xdotool获取活动窗口
    if (is_command_available("xdotool")) {
        try {
            std::string cmd = "xdotool getactivewindow";
            std::string window_id = execute_command(cmd);
            // 去除换行符
            if (!window_id.empty() && window_id.back() == '\n') {
                window_id.pop_back();
            }
            
            if (!window_id.empty()) {
                return get_window_info(window_id);
            }
        } catch (const RPAException& e) {
            std::cerr << "获取活动窗口失败: " << e.what() << std::endl;
        }
    }
    
    throw RPAException(ErrorCode::WINDOW_NOT_FOUND, "无法获取活动窗口");
}

void WindowManager::refresh_window_cache() {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    window_cache_.clear();
    
    // 预加载微信窗口信息
    try {
        WindowInfo window = find_wechat_window();
        window_cache_[window.id] = window;
    } catch (const RPAException& e) {
        // 微信窗口未找到，忽略
    }
}

void WindowManager::set_wechat_window_names(const std::vector<std::string>& names) {
    wechat_window_names_ = names;
    // 刷新缓存
    refresh_window_cache();
}

std::vector<std::string> WindowManager::get_wechat_window_names() const {
    return wechat_window_names_;
}

void WindowManager::usleep(int microseconds) const {
    ::usleep(microseconds);
}

bool WindowManager::set_window_geometry(const std::string& window_id, int x, int y, int width, int height) {
    if (!is_command_available("xdotool")) {
        std::cerr << "xdotool 不可用，无法设置窗口几何信息" << std::endl;
        return false;
    }

    try {
        // 使用 xdotool 设置窗口大小和位置
        std::string cmd = "xdotool windowsize " + window_id + " " + std::to_string(width) + " " + std::to_string(height) +
                          " && xdotool windowmove " + window_id + " " + std::to_string(x) + " " + std::to_string(y);
        execute_command(cmd);
        return true;
    } catch (const RPAException& e) {
        std::cerr << "设置窗口几何信息失败: " << e.what() << std::endl;
        return false;
    }
}

} // namespace wechat_rpa