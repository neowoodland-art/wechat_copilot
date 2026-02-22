#include "humanization_engine.h"
#include <iostream>
#include <algorithm>
#include <cmath>
#include <thread>

namespace wechat_rpa {

HumanizationEngine::HumanizationEngine() 
    : rd_(), gen_(rd_()), 
      delay_dist_(100, 500), 
      offset_dist_(-5, 5), 
      behavior_dist_(1, 100) {
}

HumanizationEngine::~HumanizationEngine() {
}

void HumanizationEngine::initialize() {
    std::cout << "[DEBUG] 拟人化引擎初始化" << std::endl;
    // 设置随机种子
    gen_.seed(std::chrono::system_clock::now().time_since_epoch().count());
}

int HumanizationEngine::get_random_delay(int min_ms, int max_ms) {
    std::uniform_int_distribution<int> dist(min_ms, max_ms);
    int delay = dist(gen_);
    std::cout << "[DEBUG] 随机延迟: " << delay << "ms" << std::endl;
    return delay;
}

int HumanizationEngine::get_random_offset(int max_offset) {
    std::uniform_int_distribution<int> dist(-max_offset, max_offset);
    int offset = dist(gen_);
    std::cout << "[DEBUG] 随机偏移: " << offset << std::endl;
    return offset;
}

void HumanizationEngine::simulate_typing(const std::string& text, int delay_ms) {
    std::cout << "[DEBUG] 模拟输入: " << text << std::endl;
    
    // 模拟逐字符输入
    for (char c : text) {
        // 随机化输入速度
        int char_delay = get_random_delay(delay_ms / 2, delay_ms * 2);
        std::this_thread::sleep_for(std::chrono::milliseconds(char_delay));
        
        // 偶尔添加删除和重输入（模拟修改）
        if (should_execute_behavior(5)) {
            // 模拟删除
            std::cout << "[DEBUG] 模拟删除字符" << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }
}

void HumanizationEngine::simulate_mouse_movement(int start_x, int start_y, int end_x, int end_y, int steps) {
    std::cout << "[DEBUG] 模拟鼠标移动: (" << start_x << "," << start_y << ") -> (" << end_x << "," << end_y << ")" << std::endl;
    
    // 计算每步的移动距离
    float dx = static_cast<float>(end_x - start_x) / steps;
    float dy = static_cast<float>(end_y - start_y) / steps;
    
    // 逐步移动
    for (int i = 0; i <= steps; i++) {
        int current_x = static_cast<int>(start_x + dx * i);
        int current_y = static_cast<int>(start_y + dy * i);
        
        // 添加随机偏移
        int offset_x = get_random_offset(2);
        int offset_y = get_random_offset(2);
        
        std::cout << "[DEBUG] 鼠标位置: (" << current_x + offset_x << "," << current_y + offset_y << ")" << std::endl;
        
        // 移动到当前位置
        std::string cmd = "xdotool mousemove " + std::to_string(current_x + offset_x) + " " + std::to_string(current_y + offset_y);
        system(cmd.c_str());
        
        // 随机延迟
        int delay = get_random_delay(20, 50);
        std::this_thread::sleep_for(std::chrono::milliseconds(delay));
    }
}

bool HumanizationEngine::should_execute_behavior(int probability) {
    std::uniform_int_distribution<int> dist(1, 100);
    int roll = dist(gen_);
    return roll <= probability;
}

} // namespace wechat_rpa