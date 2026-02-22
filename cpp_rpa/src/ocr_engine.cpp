#include "ocr_engine.h"
#include <iostream>

namespace wechat_rpa {

OCRAEngine::OCRAEngine() : initialized_(false), ocr_available_(false) {
#ifdef ENABLE_OCR
    // 初始化Tesseract
    tesseract_ = new tesseract::TessBaseAPI();
    ocr_available_ = true;
#endif
}

OCRAEngine::~OCRAEngine() {
    shutdown();
}

bool OCRAEngine::initialize(const std::string& language) {
    if (initialized_) {
        return true;
    }
    
    language_ = language;
    
#ifndef ENABLE_OCR
    std::cerr << "OCR功能未启用，请安装Tesseract" << std::endl;
    return false;
#else
    // 初始化Tesseract
    int result = tesseract_->Init(nullptr, language.c_str());
    if (result != 0) {
        std::cerr << "Tesseract初始化失败: " << result << std::endl;
        ocr_available_ = false;
        return false;
    }
    
    // 设置OCR模式
    tesseract_->SetPageSegMode(tesseract::PSM_AUTO);
    
    // 启用段落分割
    tesseract_->SetVariable("preserve_interword_spaces", "1");
    
    initialized_ = true;
    ocr_available_ = true;
    return true;
#endif
}

std::vector<TextResult> OCRAEngine::recognize_text(const cv::Mat& image) {
    if (!initialized_) {
        throw RPAException(ErrorCode::OCR_FAILED, "OCR引擎未初始化");
    }
    
#ifndef ENABLE_OCR
    throw RPAException(ErrorCode::OCR_FAILED, "OCR功能未启用");
#else
    // 确保图像是灰度图
    cv::Mat gray;
    if (image.channels() == 3) {
        cv::cvtColor(image, gray, cv::COLOR_BGR2GRAY);
    } else {
        gray = image.clone();
    }
    
    // 设置图像
    tesseract_->SetImage(gray.data, gray.cols, gray.rows, 1, gray.step);
    
    // 识别
    tesseract_->Recognize(nullptr);
    
    // 获取结果
    tesseract::ResultIterator* ri = tesseract_->GetIterator();
    tesseract::PageIteratorLevel level = tesseract::RIL_TEXTLINE;
    
    std::vector<TextResult> results;
    
    if (ri) {
        do {
            std::string text;
            float confidence;
            
            // 获取文本
            char* word = ri->GetUTF8Text(level);
            if (word) {
                text = word;
                // 去除换行符和空格
                text.erase(std::remove_if(text.begin(), text.end(), [](unsigned char c) {
                    return std::isspace(c);
                }), text.end());
                
                // 获取置信度
                confidence = ri->Confidence(level);
                
                // 获取边界框
                int x1, y1, x2, y2;
                ri->BoundingBox(level, &x1, &y1, &x2, &y2);
                
                // 创建结果
                TextResult result;
                result.text = text;
                result.confidence = confidence;
                result.region.x = x1;
                result.region.y = y1;
                result.region.width = x2 - x1;
                result.region.height = y2 - y1;
                
                // 添加到结果列表
                if (!text.empty() && confidence > 0) {
                    results.push_back(result);
                }
                
                delete[] word;
            }
        } while (ri->Next(level));
        
        delete ri;
    }
    
    return results;
#endif
}

std::vector<TextResult> OCRAEngine::recognize_region(const cv::Mat& image, const Region& region) {
    return recognize_region(image, region.x, region.y, region.width, region.height);
}

std::vector<TextResult> OCRAEngine::recognize_region(const cv::Mat& image, int x, int y, int width, int height) {
    // 确保坐标有效
    if (x < 0 || y < 0 || x + width > image.cols || y + height > image.rows) {
        throw RPAException(ErrorCode::INVALID_PARAMETER, "无效的区域坐标");
    }
    
#ifndef ENABLE_OCR
    throw RPAException(ErrorCode::OCR_FAILED, "OCR功能未启用");
#endif
    
    // 裁剪区域
    cv::Mat region_image = image(cv::Rect(x, y, width, height));
    
    // 识别
    std::vector<TextResult> results = recognize_text(region_image);
    
    // 调整坐标
    for (auto& result : results) {
        result.region.x += x;
        result.region.y += y;
    }
    
    return results;
}

bool OCRAEngine::set_language(const std::string& language) {
#ifndef ENABLE_OCR
    return false;
#endif
    
    // 关闭当前实例
    shutdown();
    
    // 重新初始化
    return initialize(language);
}

std::string OCRAEngine::get_language() const {
    return language_;
}

bool OCRAEngine::is_initialized() const {
    return initialized_;
}

bool OCRAEngine::is_ocr_available() const {
    return ocr_available_;
}

void OCRAEngine::shutdown() {
#ifdef ENABLE_OCR
    if (tesseract_) {
        tesseract_->End();
        delete tesseract_;
        tesseract_ = nullptr;
    }
#endif
    initialized_ = false;
    ocr_available_ = false;
}

} // namespace wechat_rpa