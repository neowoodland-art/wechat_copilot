# C++ RPA框架

## 项目介绍

这是一个使用C++实现的微信RPA（Robotic Process Automation）框架，提供高性能、高可靠性的微信自动化功能。

### 主要特性

- **高性能**：使用C++重写核心功能，提高执行速度和资源利用率
- **高可靠性**：减少系统调用和外部依赖，提高稳定性
- **易于集成**：通过Python绑定保持与现有Python后端的兼容性
- **功能丰富**：提供完整的微信自动化功能，包括窗口管理、截图、OCR识别和消息处理
- **可扩展性**：模块化设计，便于添加新功能和支持新平台

## 系统要求

### 硬件要求
- CPU: 至少2核
- 内存: 至少4GB
- 磁盘: 至少10GB可用空间

### 软件要求
- 操作系统: Linux (Ubuntu 18.04+, Manjaro等)
- C++编译器: GCC 7.0+ 或 Clang 6.0+
- CMake: 3.14+
- Python: 3.7+
- 依赖库:
  - OpenCV 4.0+
  - Tesseract 4.0+
  - Leptonica 1.74+
  - pybind11 2.6+

### 外部工具
- xdotool (窗口管理)
- wmctrl (窗口管理，备选)
- maim 或 scrot 或 import (截图)

## 安装步骤

### 1. 安装依赖

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install build-essential cmake libopencv-dev libleptonica-dev tesseract-ocr tesseract-ocr-chi-sim libtesseract-dev python3-dev python3-pip xdotool wmctrl maim
pip3 install pybind11
```

#### Manjaro/Arch
```bash
sudo pacman -Syu
sudo pacman -S base-devel cmake opencv tesseract tesseract-data-chi_sim leptonica python-pybind11 xdotool wmctrl maim
```

### 2. 编译安装

```bash
# 进入C++ RPA目录
cd /path/to/wechat_copilot/cpp_rpa

# 运行构建脚本
chmod +x build.sh
./build.sh
```

### 3. 验证安装

```bash
# 运行示例脚本
python examples/basic_usage.py
```

## 使用方法

### 基本使用

```python
import wechat_rpa

# 创建微信管理器
manager = wechat_rpa.WeChatManager()

# 初始化
manager.initialize()

# 激活微信
manager.activate_wechat()

# 获取最新消息
messages = manager.get_latest_messages(5)
for msg in messages:
    print(f"消息: {msg.content} (置信度: {msg.confidence:.2f})")

# 发送消息
manager.send_message("联系人名称", "你好，这是一条测试消息")
```

### 高级功能

#### AT-SPI 原子控件/容器（新）

```python
import wechat_rpa

manager = wechat_rpa.WeChatManager()
manager.initialize()

# 1) 按过滤条件查询控件
nodes = manager.query_atomic_controls({
   "role_equals": "push button",
   "expected_depth": "15",
   "name_contains": "发送",
   "require_showing": "true",
   "require_visible": "true",
})

# 2) 通过 profile 获取聊天容器
container_items = manager.get_atomic_container_by_profile("chat_message_items", "parent_path")

# 3) 通过 profile 执行动作
manager.input_text_atomic_control("chat_input_box", "你好，这是AT-SPI输入")
manager.click_atomic_control("chat_send_button")
```

配置文件位于 `config/atspi_atomic_profiles.ini`，微信版本变化后优先修改 profile 参数。

#### 截图和OCR

```python
# 截图消息区域
screenshot = manager.capture_message_area()

# 保存截图
import cv2
cv2.imwrite("screenshot.png", screenshot)

# 从截图中提取消息
messages = manager.extract_messages(screenshot)
```

#### 联系人管理

```python
# 搜索联系人
contact = manager.search_contact("关键词")
print(f"找到联系人: {contact.name} ({contact.wechat_id})")

# 获取联系人列表
contacts = manager.get_contacts(10)
for contact in contacts:
    print(f"联系人: {contact.name} ({contact.wechat_id})")
```

## 模块架构

### 核心模块

1. **WindowManager** - 窗口管理，负责查找、激活和获取窗口信息
2. **ImageProcessor** - 图像处理，负责截图、图像增强和分析
3. **OCRAEngine** - OCR引擎，负责文字识别
4. **WeChatManager** - 微信管理，整合前面的模块，提供微信相关的高级功能

### Python绑定

通过pybind11创建Python绑定，将C++类和方法暴露给Python，保持与现有Python代码的兼容性。

## 性能优化

### 内存管理
- 使用内存池减少内存分配开销
- 实现零拷贝数据传输
- 合理使用缓存减少重复计算

### 并行计算
- 使用线程池处理并发任务
- 实现任务调度算法
- 利用GPU加速图像处理和OCR

### 系统调用
- 减少系统调用次数
- 批量处理系统操作
- 优化系统调用参数

## 故障排除

### 常见问题

1. **无法找到微信窗口**
   - 确保微信已启动
   - 检查微信窗口名称是否在配置列表中
   - 尝试使用不同的窗口管理工具

2. **截图失败**
   - 确保安装了截图工具（maim, scrot或import）
   - 检查权限设置
   - 确保微信窗口可见

3. **OCR识别准确率低**
   - 确保安装了正确的语言包（如tesseract-ocr-chi-sim）
   - 调整图像增强参数
   - 尝试使用更高分辨率的截图

4. **模块导入失败**
   - 确保已正确编译和安装模块
   - 检查Python路径设置
   - 验证依赖库版本

### 日志和调试

- 运行时错误会输出到控制台
- 可以使用`print`语句调试
- 对于复杂问题，可以查看CMake构建日志

## 开发和扩展

### 目录结构

```
cpp_rpa/
├── include/          # 头文件
├── src/              # 源文件
├── bindings/         # Python绑定
├── examples/         # 示例代码
├── tests/            # 测试代码
├── CMakeLists.txt    # CMake构建文件
├── build.sh          # 构建脚本
└── README.md         # 说明文档
```

### 添加新功能

1. 在`include/`目录中创建新的头文件
2. 在`src/`目录中实现相应的功能
3. 在`bindings/python_bindings.cpp`中添加Python绑定
4. 更新`CMakeLists.txt`添加新文件
5. 重新编译安装

### 平台扩展

当前实现主要针对Linux平台，要支持其他平台：

1. 修改`WindowManager`适配不同平台的窗口管理API
2. 修改`ImageProcessor`适配不同平台的截图API
3. 调整构建脚本和依赖管理

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 联系方式

如有问题或建议，请联系项目维护者。

---

**注意**：本项目仅供学习和研究使用，请勿用于任何违反法律法规的用途。