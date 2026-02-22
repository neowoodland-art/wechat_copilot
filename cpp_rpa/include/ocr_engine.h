#ifndef WECHAT_RPA_OCR_ENGINE_H
#define WECHAT_RPA_OCR_ENGINE_H

#include "common.h"
#include <opencv2/opencv.hpp>

// 条件包含Tesseract
#ifdef ENABLE_OCR
#include <tesseract/baseapi.h>
#endif

namespace wechat_rpa {

class OCRAEngine {
private:
#ifdef ENABLE_OCR
    tesseract::TessBaseAPI* tesseract_;
#endif
    std::string language_;
    bool initialized_;
    bool ocr_available_;
    
public:
    OCRAEngine();
    ~OCRAEngine();
    
    /**
     * 初始化OCR引擎
     * @param language 语言代码，如"chi_sim"（简体中文）、"eng"（英文）
     * @return 是否初始化成功
     */
    bool initialize(const std::string& language = "chi_sim+eng");
    
    /**
     * 识别图像中的文字
     * @param image 图像
     * @return 识别结果列表
     * @throws RPAException 如果识别失败
     */
    std::vector<TextResult> recognize_text(const cv::Mat& image);
    
    /**
     * 识别指定区域的文字
     * @param image 图像
     * @param region 区域
     * @return 识别结果列表
     * @throws RPAException 如果识别失败
     */
    std::vector<TextResult> recognize_region(const cv::Mat& image, const Region& region);
    
    /**
     * 识别指定区域的文字
     * @param image 图像
     * @param x 起始X坐标
     * @param y 起始Y坐标
     * @param width 宽度
     * @param height 高度
     * @return 识别结果列表
     * @throws RPAException 如果识别失败
     */
    std::vector<TextResult> recognize_region(const cv::Mat& image, int x, int y, int width, int height);
    
    /**
     * 设置识别语言
     * @param language 语言代码
     * @return 是否设置成功
     */
    bool set_language(const std::string& language);
    
    /**
     * 获取当前识别语言
     * @return 语言代码
     */
    std::string get_language() const;
    
    /**
     * 检查引擎是否初始化
     * @return 是否已初始化
     */
    bool is_initialized() const;
    
    /**
     * 检查OCR是否可用
     * @return OCR是否可用
     */
    bool is_ocr_available() const;
    
    /**
     * 关闭OCR引擎
     */
    void shutdown();
};

} // namespace wechat_rpa

#endif // WECHAT_RPA_OCR_ENGINE_H