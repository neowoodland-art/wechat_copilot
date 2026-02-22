#include "humanization_engine.h"
#include <random>
#include <thread>
#include <chrono>
#include <iostream>

namespace wechat_rpa {

HumanizationEngine::HumanizationEngine() {
    std::random_device rd;
    gen_ = std::mt19937(rd());
}

HumanizationEngine::~HumanizationEngine() {
}

void HumanizationEngine::initialize() {
    // 初始化随机数生成器
    std::random_device rd;
    gen_ = std::mt19937(rd());
}

int HumanizationEngine::get_random_delay(int min_ms, int max_ms) {
    std::uniform_int_distribution<> dis(min_ms, max_ms);
    return dis(gen_);
}

int HumanizationEngine::get_random_offset(int max_offset) {
    std::uniform_int_distribution<> dis(-max_offset, max_offset);
    return dis(gen_);
}

void HumanizationEngine::simulate_typing(const std::string& text, int delay_ms) {
    for (char c : text) {
        // 模拟按键
        std::cout << "[HUMANIZATION] 模拟输入字符: " << c << std::endl;
        
        // 随机延迟，模拟人类打字速度的变化
        int actual_delay = delay_ms + get_random_delay(-50, 100);
        if (actual_delay > 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(actual_delay));
        }
    }
}

void HumanizationEngine::simulate_mouse_movement(int start_x, int start_y, int end_x, int end_y, int steps) {
    int dx = (end_x - start_x) / steps;
    int dy = (end_y - start_y) / steps;
    
    int x = start_x;
    int y = start_y;
    
    for (int i = 0; i <= steps; i++) {
        // 添加随机偏移，模拟人类鼠标移动的不精确性
        int offset_x = get_random_offset(2);
        int offset_y = get_random_offset(2);
        
        std::cout << "[HUMANIZATION] 鼠标移动到: (" << x + offset_x << ", " << y + offset_y << ")" << std::endl;
        
        // 随机暂停，模拟人类移动的节奏
        int pause = get_random_delay(10, 30);
        std::this_thread::sleep_for(std::chrono::milliseconds(pause));
        
        x += dx;
        y += dy;
    }
}

bool HumanizationEngine::should_execute_behavior(int probability) {
    std::uniform_int_distribution<> dis(1, 100);
    return dis(gen_) <= probability;
}

} // namespace wechat_rpa