#ifndef WECHAT_RPA_COMMON_H
#define WECHAT_RPA_COMMON_H

#include <string>
#include <vector>
#include <map>
#include <chrono>
#include <memory>
#include <stdexcept>
#include <opencv2/opencv.hpp>

namespace wechat_rpa {

// 错误码
enum class ErrorCode {
    SUCCESS = 0,
    WINDOW_NOT_FOUND,
    WINDOW_ACTIVATION_FAILED,
    SCREENSHOT_FAILED,
    OCR_FAILED,
    INPUT_SIMULATION_FAILED,
    PROCESS_NOT_FOUND,
    INVALID_PARAMETER,
    INTERNAL_ERROR,
    ELEMENT_NOT_FOUND,
    UNKNOWN_ERROR,
};

// 窗口信息结构
struct WindowInfo {
    std::string id;
    std::string title;
    int x;
    int y;
    int width;
    int height;
    bool is_active;
};

// 区域结构
struct Region {
    int x;
    int y;
    int width;
    int height;
};

// 文本识别结果
struct TextResult {
    std::string text;
    float confidence;
    Region region;
};

// 消息结构
struct Message {
    std::string id;
    std::string sender;
    std::string content;
    std::chrono::system_clock::time_point timestamp;
    float confidence;
};

// 联系人结构
struct Contact {
    std::string id;
    std::string name;
    std::string wechat_id;
    std::string avatar;
};

// SOP节点类型
enum class SOPNodeType {
    ACTION,
    DECISION,
    LOOP,
    PAUSE,
    END
};

// SOP节点
struct SOPNode {
    std::string id;
    SOPNodeType type;
    std::string name;
    std::map<std::string, std::string> properties;
    std::vector<std::string> next_nodes;
};

// SOP状态
enum class SOPStatus {
    IDLE,
    RUNNING,
    PAUSED,
    COMPLETED,
    FAILED
};

// SOP结构
struct SOP {
    std::string id;
    std::string name;
    std::string description;
    std::map<std::string, SOPNode> nodes;
    std::string start_node;
    SOPStatus status;
};

// SOP执行结果
struct SOPResult {
    bool success;
    std::string message;
    SOPStatus status;
    std::map<std::string, std::string> outputs;
};

// 基础异常类
class RPAException : public std::runtime_error {
public:
    RPAException(ErrorCode code, const std::string& message)
        : std::runtime_error(message), code_(code) {}
    
    ErrorCode code() const { return code_; }
    
private:
    ErrorCode code_;
};

// 配置键
namespace config {
    constexpr const char* WECHAT_WINDOW_NAMES = "wechat.window.names";
    constexpr const char* OCR_LANGUAGE = "ocr.language";
    constexpr const char* SCREENSHOT_QUALITY = "screenshot.quality";
    constexpr const char* ACTIVATION_TIMEOUT = "activation.timeout";
    constexpr const char* MAX_RETRY_COUNT = "max.retry.count";
}

// 微信窗口名称
const std::vector<std::string> WECHAT_WINDOW_NAMES = {
    "微信",
    "WeChat",
    "wechat"
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_COMMON_H