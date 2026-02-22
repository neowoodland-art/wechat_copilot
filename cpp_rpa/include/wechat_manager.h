#ifndef WECHAT_RPA_WECHAT_MANAGER_H
#define WECHAT_RPA_WECHAT_MANAGER_H

#include "common.h"
#include "window_manager.h"
#include "image_processor.h"
#include "ocr_engine.h"
#include "atspi_engine.h"
#include "humanization_engine.h"

namespace wechat_rpa {

class WeChatManager {
private:
    WindowManager window_manager_;
    ImageProcessor image_processor_;
    OCRAEngine ocr_engine_;
    ATSPIEngine atspi_engine_;
    HumanizationEngine humanization_engine_;
    bool initialized_;
    
    // 获取消息区域
    Region get_message_region(const WindowInfo& window) const;
    
public:
    WeChatManager();
    ~WeChatManager();
    
    /**
     * 初始化微信管理器
     * @return 是否初始化成功
     */
    bool initialize();
    
    /**
     * 激活微信
     * @return 是否激活成功
     */
    bool activate_wechat();
    
    /**
     * 获取微信窗口信息
     * @return 窗口信息
     * @throws RPAException 如果未找到窗口
     */
    WindowInfo get_wechat_window();
    
    /**
     * 检查微信是否激活
     * @return 是否激活
     */
    bool is_wechat_active();
    
    /**
     * 获取最新消息
     * @param count 获取消息数量
     * @return 消息列表
     * @throws RPAException 如果获取失败
     */
    std::vector<Message> get_latest_messages(int count = 10);
    
    /**
     * 发送消息
     * @param contact 联系人名称
     * @param message 消息内容
     * @return 是否发送成功
     */
    bool send_message(const std::string& contact, const std::string& message);
    
    /**
     * 搜索联系人
     * @param keyword 搜索关键词
     * @return 联系人信息
     */
    Contact search_contact(const std::string& keyword);
    
    /**
     * 获取联系人列表
     * @param max_count 最大数量
     * @return 联系人列表
     */
    std::vector<Contact> get_contacts(int max_count = 100);
    
    /**
     * 截图微信消息区域
     * @return 截图
     * @throws RPAException 如果截图失败
     */
    cv::Mat capture_message_area();
    
    /**
     * 截图完整微信窗口
     * @return 截图
     * @throws RPAException 如果截图失败
     */
    cv::Mat capture_full_window();
    
    /**
     * 截图微信消息区域并保存到文件
     * @param filepath 保存文件路径
     * @return 是否保存成功
     * @throws RPAException 如果截图或保存失败
     */
    bool capture_and_save_message_area(const std::string& filepath);
    
    /**
     * 查找UI元素
     * @param element_type 元素类型 (button/input/contact)
     * @return 元素区域列表
     */
    std::vector<Region> find_ui_elements(const std::string& element_type);
    
    /**
     * 获取特定元素的区域
     * @param element_name 元素名称
     * @return 元素区域
     */
    Region get_element_region(const std::string& element_name);
    
    /**
     * 截取基础界面
     * @return 基础界面图像
     */
    cv::Mat capture_base_interface();
    
    /**
     * 截取鼠标悬停时的界面
     * @param x X坐标
     * @param y Y坐标
     * @return 悬停界面图像
     */
    cv::Mat capture_hover_interface(int x, int y);
    
    /**
     * 通过鼠标移动扫描界面元素
     * @param stop_flag 停止标志指针
     * @return 元素区域列表
     */
    std::vector<Region> scan_interface_by_mouse(bool* stop_flag);
    
    /**
     * 通过鼠标移动扫描界面元素（简单版）
     * @return 元素区域列表
     */
    std::vector<Region> scan_interface_by_mouse_simple();
    
    /**
     * 通过鼠标移动扫描界面元素（带超时）
     * @param timeout_seconds 超时时间（秒）
     * @return 元素区域列表
     */
    std::vector<Region> scan_interface_by_mouse_with_timeout(int timeout_seconds);
    
    /**
     * 执行系统命令（包装方法）
     * @param command 命令字符串
     * @param timeout_ms 超时时间（毫秒）
     * @return 命令输出
     * @throws RPAException 如果命令执行失败
     */
    std::string execute_command(const std::string& command, int timeout_ms = 5000);
    
    /**
     * 线程睡眠（包装方法）
     * @param microseconds 微秒数
     */
    void usleep(int microseconds);
    
    /**
     * 使用ATSPI点击控件
     * @param control_name 控件名称
     * @return 是否成功
     */
    bool click_control_by_atspi(const std::string& control_name);
    
    /**
     * 使用ATSPI输入文本
     * @param control_name 控件名称
     * @param text 文本内容
     * @return 是否成功
     */
    bool input_text_by_atspi(const std::string& control_name, const std::string& text);
    
    /**
     * 使用ATSPI获取控件文本
     * @param control_name 控件名称
     * @return 文本内容
     */
    std::string get_control_text_by_atspi(const std::string& control_name);

    /**
     * 获取AT-SPI控件快照（用于上层树分析）
     * @param max_nodes 最大节点数
     * @return 控件信息列表
     */
    std::vector<std::map<std::string, std::string>> get_atspi_control_snapshot(int max_nodes = 300);

    /**
     * 获取AT-SPI控件树快照（包含深度与路径）
     * @param max_nodes 最大节点数
     * @param max_depth 最大递归深度（-1表示不限制）
     * @return 控件树节点列表（深度优先展开）
     */
    std::vector<std::map<std::string, std::string>> get_atspi_tree_snapshot(int max_nodes = 800, int max_depth = -1);
    
    /**
     * 拟人化点击
     * @param x 相对X坐标
     * @param y 相对Y坐标
     * @param button 鼠标按钮
     * @return 是否成功
     */
    bool humanized_click(int x, int y, int button = 1);
    
    /**
     * 拟人化输入
     * @param text 文本内容
     * @return 是否成功
     */
    bool humanized_input(const std::string& text);
    
    /**
     * 从截图中提取消息
     * @param image 截图
     * @return 消息列表
     * @throws RPAException 如果提取失败
     */
    std::vector<Message> extract_messages(const cv::Mat& image);
    
    /**
     * 确保微信处于可用状态
     * @return 是否可用
     */
    bool ensure_wechat_available();
    
    /**
     * 获取窗口管理器
     * @return 窗口管理器引用
     */
    WindowManager& get_window_manager();
    
    /**
     * 获取图像处理
     * @return 图像处理引用
     */
    ImageProcessor& get_image_processor();
    
    /**
     * 获取OCR引擎
     * @return OCR引擎引用
     */
    OCRAEngine& get_ocr_engine();
    
    /**
     * 检查是否初始化
     * @return 是否已初始化
     */
    bool is_initialized() const;
    
    /**
     * 分析界面UI元素
     * @return UI元素映射表，键为元素名称，值为元素区域
     */
    std::map<std::string, Region> analyze_ui_elements();
    
    /**
     * 查找所有按钮
     * @return 按钮区域列表
     */
    std::vector<Region> find_all_buttons();
    
    /**
     * 截图特定元素
     * @param element_name 元素名称
     * @return 元素截图
     */
    cv::Mat capture_specific_element(const std::string& element_name);
    
    /**
     * 截图并标注UI元素
     * @param element_names 要标注的元素名称列表
     * @return 标注后的截图
     */
    cv::Mat capture_and_annotate_elements(const std::vector<std::string>& element_names);
    
    /**
     * 截图并标注所有UI元素
     * @return 标注后的截图
     */
    cv::Mat capture_and_annotate_all_elements();
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_WECHAT_MANAGER_H