#include "image_processor.h"
#include <iostream>
#include <sstream>
#include <cstring>
#include <sys/wait.h>
#include <unistd.h>
#include <ctime>

namespace wechat_rpa {

ImageProcessor::ImageProcessor() {
    // 设置默认截图质量
    screenshot_quality_ = 90;
}

std::string ImageProcessor::execute_screenshot_command(const std::string& command) const {
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "无法执行截图命令: " + command);
    }
    
    char buffer[128];
    std::string result;
    
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        result += buffer;
    }
    
    pclose(pipe);
    return result;
}

cv::Mat ImageProcessor::capture_window(const WindowInfo& window) {
    return capture_region(window.x, window.y, window.width, window.height);
}

cv::Mat ImageProcessor::capture_region(const WindowInfo& window, const Region& region) {
    return capture_region(window.x + region.x, window.y + region.y, region.width, region.height);
}

cv::Mat ImageProcessor::capture_region(int x, int y, int width, int height) {
    // 修复：生成唯一的临时文件名
    std::string temp_path = "/tmp/rpa_cap_" + std::to_string(std::time(nullptr)) + ".png";
    std::string command;
    
    if (system("which maim > /dev/null 2>&1") == 0) {
        command = "maim -g " + std::to_string(width) + "x" + std::to_string(height) + 
                  "+" + std::to_string(x) + "+" + std::to_string(y) + " " + temp_path;
    } 
    else if (system("which scrot > /dev/null 2>&1") == 0) {
        command = "scrot -a " + std::to_string(x) + "," + std::to_string(y) + "," + 
                  std::to_string(width) + "," + std::to_string(height) + " " + temp_path;
    } 
    else {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "未找到截图工具（maim, scrot）");
    }
    
    if (system(command.c_str()) != 0) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "截图执行失败");
    }
    
    cv::Mat image = cv::imread(temp_path);
    unlink(temp_path.c_str());
    
    if (image.empty()) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "无法读取截图文件");
    }
    
    return image;
}

cv::Mat ImageProcessor::enhance_image(const cv::Mat& image) {
    cv::Mat enhanced;
    if (image.channels() == 3) {
        cv::cvtColor(image, enhanced, cv::COLOR_BGR2GRAY);
    } else {
        enhanced = image.clone();
    }
    
    cv::equalizeHist(enhanced, enhanced);
    cv::GaussianBlur(enhanced, enhanced, cv::Size(3, 3), 0);
    
    cv::Ptr<cv::CLAHE> clahe = cv::createCLAHE(2.0, cv::Size(8, 8));
    clahe->apply(enhanced, enhanced);
    
    return enhanced;
}

cv::Mat ImageProcessor::to_gray(const cv::Mat& image) {
    cv::Mat gray;
    if (image.channels() == 3) {
        cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    } else {
        gray = image.clone();
    }
    return gray;
}

cv::Mat ImageProcessor::binarize(const cv::Mat& image, int threshold) {
    cv::Mat gray = to_gray(image);
    cv::Mat binary;
    cv::threshold(gray, binary, threshold, 255, cv::THRESH_BINARY);
    return binary;
}

cv::Mat ImageProcessor::detect_edges(const cv::Mat& image, int low_threshold, int high_threshold) {
    cv::Mat gray = to_gray(image);
    cv::Mat edges;
    cv::Canny(gray, edges, low_threshold, high_threshold);
    return edges;
}

cv::Mat ImageProcessor::resize_image(const cv::Mat& image, int width, int height) {
    cv::Mat resized;
    cv::resize(image, resized, cv::Size(width, height));
    return resized;
}

cv::Mat ImageProcessor::resize_image(const cv::Mat& image, double scale) {
    return resize_image(image, static_cast<int>(image.cols * scale), static_cast<int>(image.rows * scale));
}

bool ImageProcessor::save_image(const cv::Mat& image, const std::string& path) {
    std::vector<int> params;
    if (path.find(".jpg") != std::string::npos || path.find(".jpeg") != std::string::npos) {
        params.push_back(cv::IMWRITE_JPEG_QUALITY);
        params.push_back(screenshot_quality_);
    } else if (path.find(".png") != std::string::npos) {
        params.push_back(cv::IMWRITE_PNG_COMPRESSION);
        params.push_back(9 - (screenshot_quality_ / 10));
    }
    return cv::imwrite(path, image, params);
}

cv::Mat ImageProcessor::load_image(const std::string& path) {
    cv::Mat image = cv::imread(path);
    if (image.empty()) {
        throw RPAException(ErrorCode::SCREENSHOT_FAILED, "无法加载图像文件: " + path);
    }
    return image;
}

void ImageProcessor::show_image(const cv::Mat& image, const std::string& window_name, int wait_ms) {
    cv::namedWindow(window_name, cv::WINDOW_NORMAL);
    cv::imshow(window_name, image);
    cv::waitKey(wait_ms);
    cv::destroyWindow(window_name);
}

void ImageProcessor::set_screenshot_quality(int quality) {
    if (quality >= 0 && quality <= 100) screenshot_quality_ = quality;
}

int ImageProcessor::get_screenshot_quality() const {
    return screenshot_quality_;
}

std::vector<Region> ImageProcessor::find_buttons(const cv::Mat& image) {
    std::vector<Region> buttons;
    cv::Mat gray, binary;
    cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    cv::threshold(gray, binary, 200, 255, cv::THRESH_BINARY_INV);
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(binary, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    for (const auto& contour : contours) {
        cv::Rect rect = cv::boundingRect(contour);
        if (rect.width > 20 && rect.height > 10 && rect.width < 200 && rect.height < 50) {
            if ((double)cv::contourArea(contour) / (rect.width * rect.height) > 0.8) {
                buttons.push_back({rect.x, rect.y, rect.width, rect.height});
            }
        }
    }
    return buttons;
}

std::vector<Region> ImageProcessor::find_input_boxes(const cv::Mat& image) {
    std::vector<Region> boxes;
    cv::Mat gray, edges;
    cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    cv::Canny(gray, edges, 50, 150);
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(edges, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    for (const auto& contour : contours) {
        cv::Rect rect = cv::boundingRect(contour);
        if (rect.width > 100 && rect.height > 20 && rect.width > rect.height * 2) {
            boxes.push_back({rect.x, rect.y, rect.width, rect.height});
        }
    }
    return boxes;
}

std::vector<Region> ImageProcessor::find_contact_items(const cv::Mat& image) {
    std::vector<Region> items;
    cv::Mat gray, binary;
    cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    cv::threshold(gray, binary, 220, 255, cv::THRESH_BINARY); // 微信侧边栏背景较浅
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(binary, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    for (const auto& contour : contours) {
        cv::Rect rect = cv::boundingRect(contour);
        if (rect.x < image.cols * 0.4 && rect.height > 30 && rect.height < 100) {
            items.push_back({rect.x, rect.y, rect.width, rect.height});
        }
    }
    return items;
}

cv::Mat ImageProcessor::detect_hover_changes(const cv::Mat& base_image, const cv::Mat& hover_image) {
    cv::Mat diff, gray_diff, binary_diff;
    cv::absdiff(base_image, hover_image, diff);
    cv::cvtColor(diff, gray_diff, cv::COLOR_BGR2GRAY);
    cv::threshold(gray_diff, binary_diff, 30, 255, cv::THRESH_BINARY);
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(binary_diff, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    cv::Mat result = hover_image.clone();
    for (const auto& contour : contours) {
        cv::Rect rect = cv::boundingRect(contour);
        cv::rectangle(result, rect, cv::Scalar(0, 255, 0), 2);
    }
    return result;
}

std::vector<Region> ImageProcessor::find_interactive_elements(const cv::Mat& base_image, const cv::Mat& hover_image) {
    std::vector<Region> elements;
    cv::Mat diff, gray_diff, binary_diff;
    cv::absdiff(base_image, hover_image, diff);
    cv::cvtColor(diff, gray_diff, cv::COLOR_BGR2GRAY);
    cv::threshold(gray_diff, binary_diff, 20, 255, cv::THRESH_BINARY);
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(binary_diff, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    for (const auto& contour : contours) {
        cv::Rect rect = cv::boundingRect(contour);
        if (rect.width > 5 && rect.height > 5) {
            elements.push_back({rect.x, rect.y, rect.width, rect.height});
        }
    }
    return elements;
}

cv::Mat ImageProcessor::capture_absolute_region(const Region& region) {
    return capture_region(region.x, region.y, region.width, region.height);
}

} // namespace wechat_rpa