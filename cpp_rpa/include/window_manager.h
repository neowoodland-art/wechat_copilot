#ifndef WECHAT_RPA_WINDOW_MANAGER_H
#define WECHAT_RPA_WINDOW_MANAGER_H

#include "common.h"
#include <mutex>
#include <unordered_map>

namespace wechat_rpa {

class WindowManager {
private:
    std::vector<std::string> wechat_window_names_;
    std::unordered_map<std::string, WindowInfo> window_cache_;
    mutable std::mutex cache_mutex_;
    int activation_timeout_;
    int max_retry_count_;
    
    // 检查命令是否可用
    bool is_command_available(const std::string& command) const;
    
    // 检查ydotool是否可用
    bool is_ydotool_available() const;

public:
    // 执行系统命令
    std::string execute_command(const std::string& command, int timeout_ms = 5000) const;
    
    // 线程睡眠
    void usleep(int microseconds) const;
    
    // 执行鼠标移动命令
    std::string execute_mouse_command(int x, int y) const;
    
    // 执行鼠标点击命令
    std::string execute_click_command(int button) const;
    
    // 使用xdotool激活窗口
    bool activate_with_xdotool(const std::string& window_id) const;
    
    // 使用wmctrl激活窗口
    bool activate_with_wmctrl(const std::string& window_name) const;
    
    // 使用enlightenment_remote激活窗口
    bool activate_with_enlightenment(const std::string& window_name) const;
    
    // 解析窗口几何信息
    WindowInfo parse_window_geometry(const std::string& window_id, const std::string& title);
    
    // 设置窗口几何信息
    bool set_window_geometry(const std::string& window_id, int x, int y, int width, int height);

public:
    WindowManager();
    
    /**
     * 查找微信窗口
     * @return 微信窗口信息
     * @throws RPAException 如果未找到窗口
     */
    WindowInfo find_wechat_window();
    
    /**
     * 激活微信窗口
     * @param window 窗口信息
     * @return 是否激活成功
     */
    bool activate_window(const WindowInfo& window);
    
    /**
     * 确保微信窗口处于激活状态
     * @return 激活结果
     */
    bool ensure_wechat_active();
    
    /**
     * 检查窗口是否激活
     * @param window 窗口信息
     * @return 是否激活
     */
    bool is_window_active(const WindowInfo& window);
    
    /**
     * 获取窗口信息
     * @param window_id 窗口ID
     * @return 窗口信息
     */
    WindowInfo get_window_info(const std::string& window_id);
    
    /**
     * 搜索窗口
     * @param window_name 窗口名称
     * @return 匹配的窗口列表
     */
    std::vector<WindowInfo> search_windows(const std::string& window_name);
    
    /**
     * 获取活动窗口
     * @return 活动窗口信息
     */
    WindowInfo get_active_window();
    
    /**
     * 刷新窗口缓存
     */
    void refresh_window_cache();
    
    /**
     * 尝试从任务栏启动微信
     */
    void try_launch_wechat_from_tray();
    
    /**
     * 设置微信窗口名称列表
     * @param names 窗口名称列表
     */
    void set_wechat_window_names(const std::vector<std::string>& names);
    
    /**
     * 获取微信窗口名称列表
     * @return 窗口名称列表
     */
    std::vector<std::string> get_wechat_window_names() const;
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_WINDOW_MANAGER_H