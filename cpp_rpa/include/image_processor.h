#ifndef WECHAT_RPA_IMAGE_PROCESSOR_H
#define WECHAT_RPA_IMAGE_PROCESSOR_H

#include "common.h"
#include <opencv2/opencv.hpp>

namespace wechat_rpa {

class ImageProcessor {
private:
    int screenshot_quality_;
    
    // 执行系统命令获取截图
    std::string execute_screenshot_command(const std::string& command) const;
    
public:
    ImageProcessor();
    
    /**
     * 截取整个窗口
     * @param window 窗口信息
     * @return 截取的图像
     * @throws RPAException 如果截图失败
     */
    cv::Mat capture_window(const WindowInfo& window);
    
    /**
     * 截取指定区域
     * @param window 窗口信息
     * @param region 区域信息
     * @return 截取的图像
     * @throws RPAException 如果截图失败
     */
    cv::Mat capture_region(const WindowInfo& window, const Region& region);
    cv::Mat capture_absolute_region(const Region& region);  // 截取绝对坐标区域
    
    /**
     * 截取指定区域
     * @param x 起始X坐标
     * @param y 起始Y坐标
     * @param width 宽度
     * @param height 高度
     * @return 截取的图像
     * @throws RPAException 如果截图失败
     */
    cv::Mat capture_region(int x, int y, int width, int height);
    
    /**
     * 图像增强
     * @param image 原始图像
     * @return 增强后的图像
     */
    cv::Mat enhance_image(const cv::Mat& image);
    
    /**
     * 灰度转换
     * @param image 原始图像
     * @return 灰度图像
     */
    cv::Mat to_gray(const cv::Mat& image);
    
    /**
     * 二值化处理
     * @param image 灰度图像
     * @param threshold 阈值
     * @return 二值化图像
     */
    cv::Mat binarize(const cv::Mat& image, int threshold = 128);
    
    /**
     * 边缘检测
     * @param image 灰度图像
     * @param low_threshold 低阈值
     * @param high_threshold 高阈值
     * @return 边缘图像
     */
    cv::Mat detect_edges(const cv::Mat& image, int low_threshold = 50, int high_threshold = 150);
    
    /**
     * 调整图像大小
     * @param image 原始图像
     * @param width 目标宽度
     * @param height 目标高度
     * @return 调整大小后的图像
     */
    cv::Mat resize_image(const cv::Mat& image, int width, int height);
    
    /**
     * 调整图像大小
     * @param image 原始图像
     * @param scale 缩放比例
     * @return 调整大小后的图像
     */
    cv::Mat resize_image(const cv::Mat& image, double scale);
    
    /**
     * 保存图像
     * @param image 图像
     * @param path 保存路径
     * @return 是否保存成功
     */
    bool save_image(const cv::Mat& image, const std::string& path);
    
    /**
     * 加载图像
     * @param path 图像路径
     * @return 加载的图像
     * @throws RPAException 如果加载失败
     */
    cv::Mat load_image(const std::string& path);
    
    /**
     * 显示图像
     * @param image 图像
     * @param window_name 窗口名称
     * @param wait_ms 等待时间（毫秒）
     */
    void show_image(const cv::Mat& image, const std::string& window_name = "Image", int wait_ms = 0);
    
    /**
     * 设置截图质量
     * @param quality 质量（0-100）
     */
    void set_screenshot_quality(int quality);
    
    /**
     * 获取截图质量
     * @return 截图质量
     */
    int get_screenshot_quality() const;
    
    /**
     * 查找按钮元素
     * @param image 输入图像
     * @return 按钮区域列表
     */
    std::vector<Region> find_buttons(const cv::Mat& image);
    
    /**
     * 查找输入框元素
     * @param image 输入图像
     * @return 输入框区域列表
     */
    std::vector<Region> find_input_boxes(const cv::Mat& image);
    
    /**
     * 查找联系人列表项
     * @param image 输入图像
     * @return 联系人区域列表
     */
    std::vector<Region> find_contact_items(const cv::Mat& image);
    
    /**
     * 检测鼠标悬停时的变化
     * @param base_image 基础图像
     * @param hover_image 悬停图像
     * @return 标记了变化区域的图像
     */
    cv::Mat detect_hover_changes(const cv::Mat& base_image, const cv::Mat& hover_image);
    
    /**
     * 查找交互元素（通过鼠标移动）
     * @param base_image 基础图像
     * @param hover_image 悬停图像
     * @return 元素区域列表
     */
    std::vector<Region> find_interactive_elements(const cv::Mat& base_image, const cv::Mat& hover_image);
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_IMAGE_PROCESSOR_H
