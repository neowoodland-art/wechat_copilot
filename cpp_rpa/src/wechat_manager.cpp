#include "wechat_manager.h"
#include <iostream>
#include <chrono>
#include <random>
#include <algorithm>

namespace wechat_rpa {

WeChatManager::WeChatManager() : initialized_(false) {
}

WeChatManager::~WeChatManager() {
}

bool WeChatManager::initialize() {
    if (initialized_) {
        return true;
    }
    
    // 初始化拟人化引擎
    humanization_engine_.initialize();
    
    // 尝试初始化ATSPI引擎
    if (!atspi_engine_.initialize()) {
        std::cerr << "ATSPI引擎初始化失败，将使用xdotool作为备选方案" << std::endl;
    }
    
    // 尝试初始化OCR引擎，但失败不会阻止整体初始化
    if (!ocr_engine_.initialize()) {
        std::cerr << "OCR引擎初始化失败，OCR功能将被禁用" << std::endl;
    }
    
    initialized_ = true;
    return true;
}

bool WeChatManager::activate_wechat() {
    return window_manager_.ensure_wechat_active();
}

WindowInfo WeChatManager::get_wechat_window() {
    return window_manager_.find_wechat_window();
}

bool WeChatManager::is_wechat_active() {
    try {
        WindowInfo window = get_wechat_window();
        return window_manager_.is_window_active(window);
    } catch (const RPAException& e) {
        std::cerr << "检查微信激活状态失败: " << e.what() << std::endl;
        return false;
    }
}

Region WeChatManager::get_message_region(const WindowInfo& window) const {
    // 计算消息区域，通常是窗口的中间部分
    Region region;
    region.x = window.width / 4;           // 左侧留1/4
    region.y = window.height / 5;          // 顶部留1/5
    region.width = window.width * 3 / 4;    // 宽度占3/4
    region.height = window.height * 3 / 5;  // 高度占3/5
    
    return region;
}

std::vector<Message> WeChatManager::get_latest_messages(int count) {
    // 确保微信激活
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    // 获取窗口信息
    WindowInfo window = get_wechat_window();
    
    // 截图消息区域
    cv::Mat screenshot = capture_message_area();
    
    // 提取消息
    std::vector<Message> messages = extract_messages(screenshot);
    
    // 限制消息数量
    if (messages.size() > count) {
        messages = std::vector<Message>(messages.end() - count, messages.end());
    }
    
    return messages;
}

bool WeChatManager::send_message(const std::string& contact, const std::string& message) {
    // 这里需要实现发送消息的逻辑
    // 1. 激活微信
    // 2. 点击搜索框
    // 3. 输入联系人名称
    // 4. 选择联系人
    // 5. 输入消息内容
    // 6. 发送消息
    
    // 暂时返回true，后续实现
    std::cout << "发送消息给 " << contact << ": " << message << std::endl;
    return true;
}

std::vector<Region> WeChatManager::find_ui_elements(const std::string& element_type) {
    std::vector<Region> elements;
    
    // 确保微信激活
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    // 获取窗口信息
    WindowInfo window = get_wechat_window();
    
    // 截取完整窗口
    cv::Mat full_window = capture_full_window();
    
    // 使用图像处理查找UI元素
    if (element_type == "button") {
        // 查找按钮元素
        elements = image_processor_.find_buttons(full_window);
    } else if (element_type == "input") {
        // 查找输入框
        elements = image_processor_.find_input_boxes(full_window);
    } else if (element_type == "contact") {
        // 查找联系人列表项
        elements = image_processor_.find_contact_items(full_window);
    }
    
    return elements;
}

Region WeChatManager::get_element_region(const std::string& element_name) {
    // 根据元素名称返回固定区域
    // 这些坐标需要根据实际微信界面调整
    
    WindowInfo window = get_wechat_window();
    
    if (element_name == "search_box") {
        // 搜索框位置
        Region region;
        region.x = window.width * 0.1;
        region.y = window.height * 0.05;
        region.width = window.width * 0.8;
        region.height = window.height * 0.05;
        return region;
    } else if (element_name == "message_input") {
        // 消息输入框位置
        Region region;
        region.x = window.width * 0.05;
        region.y = window.height * 0.85;
        region.width = window.width * 0.9;
        region.height = window.height * 0.08;
        return region;
    } else if (element_name == "send_button") {
        // 发送按钮位置
        Region region;
        region.x = window.width * 0.9;
        region.y = window.height * 0.85;
        region.width = window.width * 0.08;
        region.height = window.height * 0.08;
        return region;
    }
    
    // 默认返回空区域
    Region empty_region;
    empty_region.x = 0;
    empty_region.y = 0;
    empty_region.width = 0;
    empty_region.height = 0;
    return empty_region;
}

cv::Mat WeChatManager::capture_base_interface() {
    // 截取基础界面
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    return capture_full_window();
}

cv::Mat WeChatManager::capture_hover_interface(int x, int y) {
    // 截取鼠标悬停时的界面
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    // 移动鼠标到指定位置
    std::string result = window_manager_.execute_mouse_command(x, y);
    
    // 不检查返回值，继续执行
    // 即使命令失败，我们仍然尝试截图
    
    // 等待界面更新
    usleep(200000); // 200ms
    
    // 截取悬停后的界面
    return capture_full_window();
}

std::vector<Region> WeChatManager::scan_interface_by_mouse(bool* stop_flag) {
    std::vector<Region> all_elements;
    
    std::cout << "[DEBUG] 开始扫描界面元素..." << std::endl;
    
    // 1. 截取基础界面
    std::cout << "[DEBUG] 截取基础界面..." << std::endl;
    cv::Mat base_image = capture_base_interface();
    std::cout << "[DEBUG] 基础界面截图完成，尺寸: " << base_image.cols << "x" << base_image.rows << std::endl;
    
    // 2. 在界面上移动鼠标，扫描变化
    std::cout << "[DEBUG] 获取窗口信息..." << std::endl;
    WindowInfo window = get_wechat_window();
    std::cout << "[DEBUG] 窗口信息: 位置(" << window.x << "," << window.y << ") 大小:" << window.width << "x" << window.height << std::endl;
    
    // 从左到右，从上到下扫描
    // 注意：x和y是相对于窗口的坐标，需要转换为屏幕绝对坐标
    for (int y = 20; y < window.height - 20 && (stop_flag == nullptr || !(*stop_flag)); y += 30) {
        for (int x = 20; x < window.width - 20 && (stop_flag == nullptr || !(*stop_flag)); x += 30) {
            // 转换为屏幕绝对坐标
            int screen_x = window.x + x;
            int screen_y = window.y + y;
            
            // 移动鼠标到屏幕绝对坐标
            std::string result = window_manager_.execute_mouse_command(screen_x, screen_y);
            
            // 检查命令是否成功执行
            if (result.empty()) {
                // 命令执行失败，可能是权限问题
                std::cout << "[DEBUG] 鼠标移动命令执行失败，可能是权限问题" << std::endl;
            }
            
            // 截取悬停图像
            cv::Mat hover_image = capture_full_window();
            
            // 检测变化
            std::vector<Region> elements = image_processor_.find_interactive_elements(base_image, hover_image);
            
            // 添加到总列表
            for (const auto& elem : elements) {
                // 检查是否已存在
                bool exists = false;
                for (const auto& existing : all_elements) {
                    if (abs(existing.x - elem.x) < 10 && 
                        abs(existing.y - elem.y) < 10 &&
                        abs(existing.width - elem.width) < 10 &&
                        abs(existing.height - elem.height) < 10) {
                        exists = true;
                        break;
                    }
                }
                
                if (!exists) {
                    all_elements.push_back(elem);
                }
            }
            
            // 更新基础图像
            base_image = hover_image.clone();
            
            // 短暂延迟
            window_manager_.usleep(100000); // 100ms
        }
    }
    
    return all_elements;
}

std::string WeChatManager::execute_command(const std::string& command, int timeout_ms) {
    return window_manager_.execute_command(command, timeout_ms);
}

void WeChatManager::usleep(int microseconds) {
    window_manager_.usleep(microseconds);
}

std::vector<Region> WeChatManager::scan_interface_by_mouse_simple() {
    // 简单版本，不支持停止
    return scan_interface_by_mouse(nullptr);
}

std::vector<Region> WeChatManager::scan_interface_by_mouse_with_timeout(int timeout_seconds) {
    // 带超时的版本
    // 注意：C++版本不支持超时，超时处理在Python绑定中
    return scan_interface_by_mouse(nullptr);
}

Contact WeChatManager::search_contact(const std::string& keyword) {
    // 这里需要实现搜索联系人的逻辑
    // 暂时返回一个模拟的联系人
    Contact contact;
    contact.id = "123456";
    contact.name = keyword;
    contact.wechat_id = "wechat_id_" + keyword;
    contact.avatar = "";
    
    return contact;
}

std::vector<Contact> WeChatManager::get_contacts(int max_count) {
    // 这里需要实现获取联系人列表的逻辑
    // 暂时返回模拟数据
    std::vector<Contact> contacts;
    
    for (int i = 0; i < max_count && i < 10; ++i) {
        Contact contact;
        contact.id = std::to_string(i);
        contact.name = "联系人" + std::to_string(i);
        contact.wechat_id = "wechat_id_" + std::to_string(i);
        contact.avatar = "";
        contacts.push_back(contact);
    }
    
    return contacts;
}

cv::Mat WeChatManager::capture_message_area() {
    // 确保微信激活
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    // 获取窗口信息
    WindowInfo window = get_wechat_window();
    
    // 计算消息区域
    Region region = get_message_region(window);
    
    // 截图
    return image_processor_.capture_region(window, region);
}

cv::Mat WeChatManager::capture_full_window() {
    // 确保微信激活
    if (!activate_wechat()) {
        throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
    }
    
    // 获取窗口信息
    WindowInfo window = get_wechat_window();
    
    // 截取整个窗口
    Region full_window;
    full_window.x = 0;
    full_window.y = 0;
    full_window.width = window.width;
    full_window.height = window.height;
    
    return image_processor_.capture_region(window, full_window);
}


std::vector<Message> WeChatManager::extract_messages(const cv::Mat& image) {
    // 转换为消息
    std::vector<Message> messages;
    
    // 检查OCR是否可用
    if (!ocr_engine_.is_ocr_available()) {
        std::cerr << "OCR功能不可用，无法提取消息" << std::endl;
        return messages;
    }
    
    try {
        // 增强图像
        cv::Mat enhanced = image_processor_.enhance_image(image);
        
        // OCR识别
        std::vector<TextResult> text_results = ocr_engine_.recognize_text(enhanced);
        
        // 模拟消息生成，后续需要根据实际OCR结果进行更复杂的处理
        for (size_t i = 0; i < text_results.size(); ++i) {
            const TextResult& result = text_results[i];
            
            if (result.text.empty() || result.confidence < 0.6) {
                continue;
            }
            
            Message message;
            message.id = std::to_string(i);
            message.sender = "联系人" + std::to_string(i % 5);
            message.content = result.text;
            message.timestamp = std::chrono::system_clock::now();
            message.confidence = result.confidence;
            
            messages.push_back(message);
        }
    } catch (const RPAException& e) {
        std::cerr << "提取消息失败: " << e.what() << std::endl;
    }
    
    return messages;
}

bool WeChatManager::ensure_wechat_available() {
    try {
        // 检查微信是否激活
        if (!is_wechat_active()) {
            // 尝试激活
            if (!activate_wechat()) {
                return false;
            }
        }
        
        // 检查窗口是否存在
        get_wechat_window();
        
        return true;
    } catch (const RPAException& e) {
        std::cerr << "微信不可用: " << e.what() << std::endl;
        return false;
    }
}

WindowManager& WeChatManager::get_window_manager() {
    return window_manager_;
}

ImageProcessor& WeChatManager::get_image_processor() {
    return image_processor_;
}

OCRAEngine& WeChatManager::get_ocr_engine() {
    return ocr_engine_;
}

bool WeChatManager::is_initialized() const {
    return initialized_;
}

bool WeChatManager::click_control_by_atspi(const std::string& control_name) {
    try {
        // 获取微信应用
        AtspiAccessible* app = atspi_engine_.get_wechat_application();
        if (!app) {
            std::cerr << "[ERROR] 无法获取微信应用" << std::endl;
            return false;
        }
        
        // 查找控件
        std::vector<AtspiAccessible*> controls = atspi_engine_.find_controls_by_name(app, control_name);
        if (controls.empty()) {
            std::cerr << "[ERROR] 未找到控件: " << control_name << std::endl;
            return false;
        }
        
        // 点击第一个匹配的控件
        bool result = atspi_engine_.click_control(controls[0]);
        
        // 清理资源
        for (auto* control : controls) {
            if (control) {
                g_object_unref(control);
            }
        }
        g_object_unref(app);
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] ATSPI点击控件失败: " << e.what() << std::endl;
        return false;
    }
}

bool WeChatManager::input_text_by_atspi(const std::string& control_name, const std::string& text) {
    try {
        // 获取微信应用
        AtspiAccessible* app = atspi_engine_.get_wechat_application();
        if (!app) {
            std::cerr << "[ERROR] 无法获取微信应用" << std::endl;
            return false;
        }
        
        // 查找控件
        std::vector<AtspiAccessible*> controls = atspi_engine_.find_controls_by_name(app, control_name);
        if (controls.empty()) {
            std::cerr << "[ERROR] 未找到控件: " << control_name << std::endl;
            return false;
        }
        
        // 输入文本到第一个匹配的控件
        bool result = atspi_engine_.input_text(controls[0], text);
        
        // 清理资源
        for (auto* control : controls) {
            if (control) {
                g_object_unref(control);
            }
        }
        g_object_unref(app);
        
        return result;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] ATSPI输入文本失败: " << e.what() << std::endl;
        return false;
    }
}

std::string WeChatManager::get_control_text_by_atspi(const std::string& control_name) {
    try {
        // 获取微信应用
        AtspiAccessible* app = atspi_engine_.get_wechat_application();
        if (!app) {
            std::cerr << "[ERROR] 无法获取微信应用" << std::endl;
            return "";
        }
        
        // 查找控件
        std::vector<AtspiAccessible*> controls = atspi_engine_.find_controls_by_name(app, control_name);
        if (controls.empty()) {
            std::cerr << "[ERROR] 未找到控件: " << control_name << std::endl;
            return "";
        }
        
        // 获取第一个匹配控件的文本
        std::string text = atspi_engine_.get_control_text(controls[0]);
        
        // 清理资源
        for (auto* control : controls) {
            if (control) {
                g_object_unref(control);
            }
        }
        g_object_unref(app);
        
        return text;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] ATSPI获取控件文本失败: " << e.what() << std::endl;
        return "";
    }
}

std::vector<std::map<std::string, std::string>> WeChatManager::get_atspi_control_snapshot(int max_nodes) {
    std::vector<std::map<std::string, std::string>> snapshot;

    try {
        AtspiAccessible* app = atspi_engine_.get_wechat_application();
        if (!app) {
            return snapshot;
        }

        std::vector<AtspiAccessible*> controls = atspi_engine_.get_all_controls(app);
        int limit = std::max(1, max_nodes);

        for (int i = 0; i < static_cast<int>(controls.size()) && static_cast<int>(snapshot.size()) < limit; ++i) {
            AtspiAccessible* control = controls[i];
            if (!control) {
                continue;
            }

            std::string name = atspi_engine_.get_control_name(control);
            std::string role = atspi_engine_.get_control_role(control);
            std::string text = atspi_engine_.get_control_text(control);
            Region region = atspi_engine_.get_control_region(control);

            std::map<std::string, std::string> item;
            item["index"] = std::to_string(i);
            item["name"] = name;
            item["role"] = role;
            item["text"] = text;
            item["x"] = std::to_string(region.x);
            item["y"] = std::to_string(region.y);
            item["width"] = std::to_string(region.width);
            item["height"] = std::to_string(region.height);
            snapshot.push_back(item);
        }

#ifdef HAVE_ATSPI
        for (auto* control : controls) {
            if (control) {
                g_object_unref(control);
            }
        }
        g_object_unref(app);
#endif

        return snapshot;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 获取AT-SPI控件快照失败: " << e.what() << std::endl;
        return snapshot;
    }
}

std::vector<std::map<std::string, std::string>> WeChatManager::get_atspi_tree_snapshot(int max_nodes, int max_depth) {
    std::vector<std::map<std::string, std::string>> snapshot;
    int limit = std::max(1, max_nodes);

#ifdef HAVE_ATSPI
    try {
        AtspiAccessible* app = atspi_engine_.get_wechat_application();
        if (!app) {
            return snapshot;
        }

        struct StackItem {
            AtspiAccessible* node;
            int depth;
            int parent_index;
            std::string path;
        };

        std::vector<StackItem> stack;
        stack.push_back({app, 0, -1, "Root"});

        while (!stack.empty() && static_cast<int>(snapshot.size()) < limit) {
            StackItem current = stack.back();
            stack.pop_back();

            AtspiAccessible* node = current.node;
            if (!node) {
                continue;
            }

            std::string name = atspi_engine_.get_control_name(node);
            std::string role = atspi_engine_.get_control_role(node);
            std::string text = atspi_engine_.get_control_text(node);
            Region region = atspi_engine_.get_control_region(node);

            int current_index = static_cast<int>(snapshot.size());
            std::map<std::string, std::string> item;
            item["index"] = std::to_string(current_index);
            item["name"] = name;
            item["role"] = role;
            item["text"] = text;
            item["x"] = std::to_string(region.x);
            item["y"] = std::to_string(region.y);
            item["width"] = std::to_string(region.width);
            item["height"] = std::to_string(region.height);
            item["depth"] = std::to_string(current.depth);
            item["parent_index"] = std::to_string(current.parent_index);
            item["path"] = current.path;
            snapshot.push_back(item);

            if (max_depth >= 0 && current.depth >= max_depth) {
                continue;
            }

            GError* error = nullptr;
            gint child_count = atspi_accessible_get_child_count(node, &error);
            if (error) {
                g_error_free(error);
                error = nullptr;
                continue;
            }

            for (gint i = child_count - 1; i >= 0; --i) {
                AtspiAccessible* child = atspi_accessible_get_child_at_index(node, i, &error);
                if (error) {
                    g_error_free(error);
                    error = nullptr;
                    continue;
                }
                if (!child) {
                    continue;
                }

                std::string child_path = current.path + " -> Child[" + std::to_string(i) + "]";
                stack.push_back({child, current.depth + 1, current_index, child_path});
            }
        }

        g_object_unref(app);
        return snapshot;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 获取AT-SPI树快照失败: " << e.what() << std::endl;
        return snapshot;
    }
#else
    return snapshot;
#endif
}

bool WeChatManager::humanized_click(int x, int y, int button) {
    try {
        // 获取窗口信息
        WindowInfo window = get_wechat_window();
        
        // 转换为绝对坐标
        int abs_x = window.x + x;
        int abs_y = window.y + y;
        
        // 获取随机偏移
        int offset_x = humanization_engine_.get_random_offset(5);
        int offset_y = humanization_engine_.get_random_offset(5);
        
        // 获取当前鼠标位置（如果可能）
        std::string get_pos_cmd = "xdotool getmouselocation";
        std::string result = window_manager_.execute_command(get_pos_cmd, 500);
        
        int current_x = 0, current_y = 0;
        if (!result.empty()) {
            // 解析当前位置
            size_t x_pos = result.find("x:");
            size_t y_pos = result.find("y:");
            if (x_pos != std::string::npos && y_pos != std::string::npos) {
                sscanf(result.substr(x_pos).c_str(), "x:%d", &current_x);
                sscanf(result.substr(y_pos).c_str(), "y:%d", &current_y);
            }
        }
        
        // 模拟鼠标移动轨迹
        humanization_engine_.simulate_mouse_movement(
            current_x, current_y, 
            abs_x + offset_x, abs_y + offset_y
        );
        
        // 随机延迟
        int delay = humanization_engine_.get_random_delay(100, 300);
        usleep(delay * 1000);
        
        // 执行点击
        std::string click_cmd = "xdotool click " + std::to_string(button);
        window_manager_.execute_command(click_cmd, 500);
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 拟人化点击失败: " << e.what() << std::endl;
        return false;
    }
}

bool WeChatManager::humanized_input(const std::string& text) {
    try {
        // 模拟人类输入速度
        humanization_engine_.simulate_typing(text);
        
        // 实际输入文本
        std::string input_cmd = "xdotool type '" + text + "'";
        window_manager_.execute_command(input_cmd, 500);
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] 拟人化输入失败: " << e.what() << std::endl;
        return false;
    }
}

std::map<std::string, Region> WeChatManager::analyze_ui_elements() {
    std::map<std::string, Region> elements;
    
    try {
        // 确保微信激活
        if (!activate_wechat()) {
            throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
        }
        
        // 获取微信窗口
        WindowInfo window = get_wechat_window();
        
        // 添加预定义的UI元素
        // 搜索框
        Region search_box;
        search_box.x = window.width * 0.1;
        search_box.y = window.height * 0.05;
        search_box.width = window.width * 0.8;
        search_box.height = window.height * 0.05;
        elements["search_box"] = search_box;
        
        // 消息输入框
        Region message_input;
        message_input.x = window.width * 0.05;
        message_input.y = window.height * 0.85;
        message_input.width = window.width * 0.75;
        message_input.height = window.height * 0.08;
        elements["message_input"] = message_input;
        
        // 发送按钮
        Region send_button;
        send_button.x = window.width * 0.82;
        send_button.y = window.height * 0.85;
        send_button.width = window.width * 0.15;
        send_button.height = window.height * 0.08;
        elements["send_button"] = send_button;
        
        // 聊天区域
        Region chat_area;
        chat_area.x = window.width * 0.05;
        chat_area.y = window.height * 0.15;
        chat_area.width = window.width * 0.9;
        chat_area.height = window.height * 0.65;
        elements["chat_area"] = chat_area;
        
        // 联系人列表区域
        Region contact_list;
        contact_list.x = 0;
        contact_list.y = 0;
        contact_list.width = window.width * 0.3;
        contact_list.height = window.height;
        elements["contact_list"] = contact_list;
        
        // 主聊天窗口区域
        Region main_chat;
        main_chat.x = window.width * 0.3;
        main_chat.y = 0;
        main_chat.width = window.width * 0.7;
        main_chat.height = window.height;
        elements["main_chat"] = main_chat;
        
        // 使用ATSPI引擎获取更多UI元素（如果可用）
        if (atspi_engine_.initialize() && atspi_engine_.get_wechat_application() != nullptr) {
            AtspiAccessible* app = atspi_engine_.get_wechat_application();
            if (app) {
                // 查找所有按钮
                std::vector<AtspiAccessible*> buttons = atspi_engine_.find_controls_by_role(app, "push button");
                for (size_t i = 0; i < buttons.size(); ++i) {
                    Region region = atspi_engine_.get_control_region(buttons[i]);
                    Region button_region;
                    button_region.x = region.x;
                    button_region.y = region.y;
                    button_region.width = region.width;
                    button_region.height = region.height;
                    elements["button_" + std::to_string(i)] = button_region;
                }
                
                // 清理资源
                for (auto* button : buttons) {
                    if (button) {
                        g_object_unref(button);
                    }
                }
                g_object_unref(app);
            }
        }
        
    } catch (const RPAException& e) {
        std::cerr << "分析UI元素失败: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "分析UI元素异常: " << e.what() << std::endl;
    }
    
    return elements;
}

std::vector<Region> WeChatManager::find_all_buttons() {
    std::vector<Region> buttons;
    
    try {
        // 确保微信激活
        if (!activate_wechat()) {
            throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
        }
        
        // 获取微信窗口
        WindowInfo window = get_wechat_window();
        
        // 预定义一些常见的按钮位置
        // 发送按钮
        Region send_button;
        send_button.x = window.width * 0.82;
        send_button.y = window.height * 0.85;
        send_button.width = window.width * 0.15;
        send_button.height = window.height * 0.08;
        buttons.push_back(send_button);
        
        // 添加更多预定义按钮...
        // 聊天设置按钮
        Region settings_button;
        settings_button.x = window.width - 50;
        settings_button.y = 20;
        settings_button.width = 30;
        settings_button.height = 30;
        buttons.push_back(settings_button);
        
        // 使用ATSPI引擎查找所有按钮（如果可用）
        if (atspi_engine_.initialize() && atspi_engine_.get_wechat_application() != nullptr) {
            AtspiAccessible* app = atspi_engine_.get_wechat_application();
            if (app) {
                std::vector<AtspiAccessible*> atspi_buttons = atspi_engine_.find_controls_by_role(app, "push button");
                for (auto* btn : atspi_buttons) {
                    if (btn) {
                        Region region = atspi_engine_.get_control_region(btn);
                        Region button_region;
                        button_region.x = region.x;
                        button_region.y = region.y;
                        button_region.width = region.width;
                        button_region.height = region.height;
                        buttons.push_back(button_region);
                        
                        g_object_unref(btn);
                    }
                }
                g_object_unref(app);
            }
        }
        
    } catch (const RPAException& e) {
        std::cerr << "查找按钮失败: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "查找按钮异常: " << e.what() << std::endl;
    }
    
    return buttons;
}

cv::Mat WeChatManager::capture_specific_element(const std::string& element_name) {
    try {
        // 确保微信激活
        if (!activate_wechat()) {
            throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
        }
        
        // 获取元素区域
        Region element_region = get_element_region(element_name);
        
        // 如果通过get_element_region无法获取到区域，则尝试通过UI分析获取
        if (element_region.width == 0 && element_region.height == 0) {
            std::map<std::string, Region> elements = analyze_ui_elements();
            auto it = elements.find(element_name);
            if (it != elements.end()) {
                element_region = it->second;
            } else {
                // 如果仍然找不到，抛出异常
                throw RPAException(ErrorCode::WINDOW_NOT_FOUND, "未找到指定元素: " + element_name);
            }
        }
        
        // 获取窗口信息
        WindowInfo window = get_wechat_window();
        
        // 调整区域坐标为绝对坐标
        Region absolute_region;
        absolute_region.x = window.x + element_region.x;
        absolute_region.y = window.y + element_region.y;
        absolute_region.width = element_region.width;
        absolute_region.height = element_region.height;
        
        // 截取特定元素区域
        cv::Mat element_screenshot = image_processor_.capture_absolute_region(absolute_region);
        
        return element_screenshot;
        
    } catch (const RPAException& e) {
        std::cerr << "截图特定元素失败: " << e.what() << std::endl;
        throw;
    } catch (const std::exception& e) {
        std::cerr << "截图特定元素异常: " << e.what() << std::endl;
        throw RPAException(ErrorCode::UNKNOWN_ERROR, "截图特定元素异常: " + std::string(e.what()));
    }
}


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
// 实现capture_and_annotate_elements方法
cv::Mat WeChatManager::capture_and_annotate_elements(const std::vector<std::string>& element_names) {
    try {
        // 确保微信激活
        if (!activate_wechat()) {
            throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
        }
        
        // 截图整个微信窗口
        cv::Mat screenshot = capture_full_window();
        
        // 检查截图是否有效
        if (screenshot.empty()) {
            throw RPAException(ErrorCode::SCREENSHOT_FAILED, "截图为空");
        }
        
        // 获取窗口信息用于坐标转换
        WindowInfo window = get_wechat_window();
        
        // 分析所有UI元素
        std::map<std::string, Region> elements = analyze_ui_elements();
        
        int idx = 0;
        for (const auto& element_name : element_names) {
            auto it = elements.find(element_name);
            if (it != elements.end()) {
                const Region& element_region = it->second;
                
                // 转换为绝对坐标
                cv::Point top_left(window.x + element_region.x, window.y + element_region.y);
                cv::Point bottom_right(window.x + element_region.x + element_region.width, 
                                      window.y + element_region.y + element_region.height);
                
                // 确保坐标在图像边界内
                top_left.x = std::max(0, top_left.x);
                top_left.y = std::max(0, top_left.y);
                bottom_right.x = std::min(screenshot.cols, bottom_right.x);
                bottom_right.y = std::min(screenshot.rows, bottom_right.y);
                
                // 检查坐标是否有效
                if (top_left.x >= screenshot.cols || top_left.y >= screenshot.rows || 
                    bottom_right.x <= top_left.x || bottom_right.y <= top_left.y) {
                    continue;  // 跳过无效的区域
                }
                
                // 使用红色绘制矩形框
                cv::Scalar color(0, 0, 255);  // 红色
                
                // 绘制矩形框
                cv::rectangle(screenshot, top_left, bottom_right, color, 2);
                
                // 在矩形上方添加文字标签
                int text_y = std::max(15, top_left.y - 5);
                // 确保文本位置在图像范围内
                if (text_y < 0) text_y = top_left.y + 15;
                if (text_y >= screenshot.rows) text_y = screenshot.rows - 5;
                
                cv::Point text_pos(std::max(0, top_left.x), text_y);
                std::string label = element_name + "(" + std::to_string(idx) + ")";
                cv::putText(screenshot, label, text_pos, cv::FONT_HERSHEY_SIMPLEX, 0.4, color, 1);
                
                idx++;
            }
        }
        
        return screenshot;
        
    } catch (const RPAException& e) {
        std::cerr << "截图并标注指定元素失败: " << e.what() << std::endl;
        throw;
    } catch (const std::exception& e) {
        std::cerr << "截图并标注指定元素异常: " << e.what() << std::endl;
        throw RPAException(ErrorCode::UNKNOWN_ERROR, std::string("截图并标注指定元素异常: ") + e.what());
    }
}

// 实现capture_and_annotate_all_elements方法
cv::Mat WeChatManager::capture_and_annotate_all_elements() {
    try {
        // 确保微信激活
        if (!activate_wechat()) {
            throw RPAException(ErrorCode::WINDOW_ACTIVATION_FAILED, "微信激活失败");
        }
        
        // 截图整个微信窗口
        cv::Mat screenshot = capture_full_window();
        
        // 检查截图是否有效
        if (screenshot.empty()) {
            throw RPAException(ErrorCode::SCREENSHOT_FAILED, "截图为空");
        }
        
        // 获取窗口信息用于坐标转换
        WindowInfo window = get_wechat_window();
        
        // 分析所有UI元素
        std::map<std::string, Region> elements = analyze_ui_elements();
        
        int idx = 0;
        for (const auto& pair : elements) {
            const std::string& element_name = pair.first;
            const Region& element_region = pair.second;
            
            // 转换为绝对坐标
            cv::Point top_left(window.x + element_region.x, window.y + element_region.y);
            cv::Point bottom_right(window.x + element_region.x + element_region.width, 
                                  window.y + element_region.y + element_region.height);
            
            // 确保坐标在图像边界内
            top_left.x = std::max(0, top_left.x);
            top_left.y = std::max(0, top_left.y);
            bottom_right.x = std::min(screenshot.cols, bottom_right.x);
            bottom_right.y = std::min(screenshot.rows, bottom_right.y);
            
            // 检查坐标是否有效
            if (top_left.x >= screenshot.cols || top_left.y >= screenshot.rows || 
                bottom_right.x <= top_left.x || bottom_right.y <= top_left.y) {
                continue;  // 跳过无效的区域
            }
            
            // 使用不同颜色区分不同的元素类型
            cv::Scalar color;
            if (element_name.find("button") != std::string::npos || 
                element_name.find("Button") != std::string::npos || 
                element_name.find("btn") != std::string::npos) {
                color = cv::Scalar(0, 0, 255);  // 红色表示按钮
            } else if (element_name.find("input") != std::string::npos || 
                       element_name.find("edit") != std::string::npos || 
                       element_name.find("Edit") != std::string::npos) {
                color = cv::Scalar(255, 0, 0);  // 蓝色表示输入框
            } else {
                color = cv::Scalar(0, 255, 0);  // 绿色表示其他元素
            }
            
            // 绘制矩形框
            cv::rectangle(screenshot, top_left, bottom_right, color, 2);
            
            // 在矩形上方添加文字标签
            int text_y = std::max(15, top_left.y - 5);
            // 确保文本位置在图像范围内
            if (text_y < 0) text_y = top_left.y + 15;
            if (text_y >= screenshot.rows) text_y = screenshot.rows - 5;
            
            cv::Point text_pos(std::max(0, top_left.x), text_y);
            std::string label = element_name + "(" + std::to_string(idx) + ")";
            cv::putText(screenshot, label, text_pos, cv::FONT_HERSHEY_SIMPLEX, 0.4, color, 1);
            
            idx++;
        }
        
        return screenshot;
        
    } catch (const RPAException& e) {
        std::cerr << "截图并标注所有元素失败: " << e.what() << std::endl;
        throw;
    } catch (const std::exception& e) {
        std::cerr << "截图并标注所有元素异常: " << e.what() << std::endl;
        throw RPAException(ErrorCode::UNKNOWN_ERROR, std::string("截图并标注所有元素异常: ") + e.what());
    }
}

}  // namespace wechat_rpa