#ifndef WECHAT_RPA_HUMANIZATION_ENGINE_H
#define WECHAT_RPA_HUMANIZATION_ENGINE_H

#include <random>
#include <chrono>
#include <thread>

namespace wechat_rpa {

/**
 * 拟人化引擎 - 模拟人类行为
 * 用于避免被检测为自动化工具
 */
class HumanizationEngine {
public:
    HumanizationEngine();
    ~HumanizationEngine();
    
    /**
     * 初始化拟人化引擎
     */
    void initialize();
    
    /**
     * 获取随机延迟
     * @param min_ms 最小延迟（毫秒）
     * @param max_ms 最大延迟（毫秒）
     * @return 延迟时间（毫秒）
     */
    int get_random_delay(int min_ms = 100, int max_ms = 500);
    
    /**
     * 获取随机偏移
     * @param max_offset 最大偏移值
     * @return 偏移值
     */
    int get_random_offset(int max_offset = 5);
    
    /**
     * 模拟人类输入速度
     * @param text 输入文本
     * @param delay_ms 字符间延迟（毫秒）
     */
    void simulate_typing(const std::string& text, int delay_ms = 100);
    
    /**
     * 模拟人类移动轨迹
     * @param start_x 起始X坐标
     * @param start_y 起始Y坐标
     * @param end_x 结束X坐标
     * @param end_y 结束Y坐标
     * @param steps 移动步数
     */
    void simulate_mouse_movement(int start_x, int start_y, int end_x, int end_y, int steps = 10);
    
    /**
     * 获取随机行为概率
     * @param probability 行为概率（0-100）
     * @return 是否执行行为
     */
    bool should_execute_behavior(int probability);
    
private:
    std::random_device rd_;
    std::mt19937 gen_;
    std::uniform_int_distribution<int> delay_dist_;
    std::uniform_int_distribution<int> offset_dist_;
    std::uniform_int_distribution<int> behavior_dist_;
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_HUMANIZATION_ENGINE_H