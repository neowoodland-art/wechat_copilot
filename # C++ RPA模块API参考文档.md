# C++ RPA 模块 API 参考文档

> 目标：为 `cpp_rpa` 独立项目化准备统一 API 说明、脚本入口与测试方法。

## 1. 模块入口

### 1.1 Python 绑定导入
```python
import sys
sys.path.insert(0, 'cpp_rpa/build')
import wechat_rpa
```

### 1.2 对外核心类
- `WeChatManager`
- `ATSPIEngine`
- `WindowManager`
- `ImageProcessor`
- `OCREngine`
- `HumanizationEngine`

## 2. WeChatManager 主要 API

### 2.1 生命周期与窗口
- `initialize() -> bool`
- `activate_wechat() -> bool`
- `is_wechat_active() -> bool`
- `get_wechat_window() -> WindowInfo`

### 2.2 消息操作
- `get_latest_messages(count=10) -> list[Message]`
- `send_message(contact, message) -> bool`

### 2.3 截图与界面分析
- `capture_message_area() -> cv::Mat`
- `capture_full_window() -> cv::Mat`
- `capture_base_interface() -> cv::Mat`
- `analyze_ui_elements() -> map<string, Region>`
- `find_all_buttons() -> list[Region]`
- `capture_specific_element(element_name) -> cv::Mat`

### 2.4 ATSPI 协同
- `click_control_by_atspi(control_name) -> bool`
- `input_text_by_atspi(control_name, text) -> bool`
- `get_control_text_by_atspi(control_name) -> str`
- `get_atspi_control_snapshot() -> list[dict]`
- `get_atspi_tree_snapshot(max_nodes, max_depth) -> list[dict]`

## 3. ATSPIEngine 主要 API

### 3.1 基础
- `initialize() -> bool`
- `init(app_name="WeChat") -> bool`
- `find_control(conditions, max_depth=8, start_from=None)`
- `get_control_info(control) -> ControlInfo`
- `click_control(control) -> bool`
- `set_text(control, text) -> bool`
- `focus_control(control) -> bool`

### 3.2 微信扩展
- `get_contact_list() -> list[ControlInfo]`
- `get_chat_history(max_count=50) -> list[ControlInfo]`
- `send_message_to_contact(contact, content) -> bool`

### 3.3 调试
- `dump_tree(root, depth=0) -> str`

## 4. 其他核心类职责
- `WindowManager`：窗口查找、激活、移动、尺寸控制、命令执行。
- `ImageProcessor`：图像增强、裁剪、边缘/区域处理。
- `OCREngine`：文本识别与候选提取。
- `HumanizationEngine`：拟人化延迟、输入节奏与随机偏移。

## 5. 关键数据结构
- `WindowInfo`：`id/title/x/y/width/height/is_active`
- `Region`：`x/y/width/height`
- `Message`：`sender/content/timestamp/confidence`
- `ControlInfo`：`name/role/value/x/y/width/height/is_focusable`

## 6. 启动与测试脚本

### 6.1 构建脚本
```bash
cd cpp_rpa
./build.sh
# 编译异常可使用
./build_fixed.sh
# 全清理重构建
./rebuild.sh
```

### 6.2 联测脚本
```bash
python cpp_rpa/simple_test.py
python cpp_rpa/test_wechat_window.py
python cpp_rpa/test_atspi.py
python cpp_rpa/test_cpp_atspi_only.py
python cpp_rpa/test_humanization.py
```

### 6.3 脚本用途
- `build.sh`：标准构建。
- `build_fixed.sh`：修复型构建（异常优先）。
- `build_and_test.sh`：构建 + 基础测试。
- `compile_and_run.sh`：快速编译运行。
- `install_deps.sh/install_atspi.sh/install_ydotool.sh`：环境准备。

## 7. 与后端 API 的封装关系
- C++ 模块由 Python 绑定导出，后端通过 `backend/api/v1/rpa*.py` 调用。
- 扫描、构建、标注确认等框架能力在后端路由层完成组合封包。
- 建议上层统一走后端 API，不直接跨层耦合底层引擎细节。

## 8. 稳定性与独立化要求
1. 保留多层降级策略（AT-SPI -> 几何/坐标 -> 键盘/OCR）。
2. 保留诊断信息输出（策略、耗时、节点数量、错误原因）。
3. 保持 `include/src/bindings/examples` 结构稳定。
4. API 文档与构建/测试脚本同步更新。

## 9. 2026-02-22 更新记录
- 适配上层扫描任务异步化后的对接说明。
- 强化“区域范围优先命中 + 差分调试摘要”在封包层的协同要求。
- 文档整理为可直接拆分成独立 C++ 项目时可复用版本。
