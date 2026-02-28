# C++ RPA 模块 API 参考文档

> 目标：为 `cpp_rpa` 独立项目化准备统一 API 说明、脚本入口与测试方法。
> 说明：以下 API 以 `cpp_rpa/bindings/python_bindings.cpp` 与头文件为准。

## 1. 模块入口

### 1.1 Python 绑定导入
```python
import sys
sys.path.insert(0, 'cpp_rpa/build')
import wechat_rpa
```

### 1.2 对外核心类（Python 绑定）
- `WeChatManager`
- `ATSPIEngine`
- `WindowManager`
- `ImageProcessor`
- `OCRAEngine`
- `HumanizationEngine`

## 2. WeChatManager 主要 API

### 2.1 生命周期与窗口
- `initialize() -> bool`
- `is_initialized() -> bool`
- `ensure_wechat_available() -> bool`
- `activate_wechat() -> bool`
- `is_wechat_active() -> bool`
- `get_wechat_window() -> WindowInfo`

### 2.2 消息与联系人
- `get_latest_messages(count=10) -> list[Message]`
- `send_message(contact, message) -> bool`
- `search_contact(keyword) -> Contact`
- `get_contacts(max_count=100) -> list[Contact]`

### 2.3 截图与界面分析
- `capture_message_area() -> numpy.ndarray`
- `capture_full_window() -> numpy.ndarray`
- `capture_base_interface() -> numpy.ndarray`
- `capture_specific_element(element_name) -> numpy.ndarray`
- `capture_and_save_message_area(filepath) -> bool`
- `capture_and_annotate_elements(element_names) -> numpy.ndarray`
- `capture_and_annotate_all_elements() -> numpy.ndarray`
- `find_ui_elements(element_type) -> list[Region]`
- `find_all_buttons() -> list[Region]`
- `analyze_ui_elements() -> map[str, Region]`
- `get_element_region(element_name) -> Region`

### 2.4 AT-SPI 协同（传统）
- `click_control_by_atspi(control_name) -> bool`
- `input_text_by_atspi(control_name, text) -> bool`
- `get_control_text_by_atspi(control_name) -> str`
- `get_atspi_control_snapshot(max_nodes=300) -> list[dict]`
- `get_atspi_tree_snapshot(max_nodes=800, max_depth=-1) -> list[dict]`

### 2.5 AT-SPI 原子控件与 Profile
- `query_atomic_controls(filters, max_nodes=1600, max_depth=-1) -> list[dict]`
- `get_atomic_container_by_profile(profile_name, group_by="parent_path", max_nodes=1800, max_depth=-1) -> list[dict]`
- `list_atomic_profiles() -> list[str]`
- `refresh_atomic_profile(profile_name, max_nodes=2200, max_depth=24) -> dict`
- `find_chat_atomic_groups(max_nodes=2200, max_depth=24) -> list[dict]`
- `detect_popup_atomic_controls(max_nodes=1600, max_depth=24) -> list[dict]`
- `click_atomic_control(profile_name) -> bool`
- `input_text_atomic_control(profile_name, text) -> bool`
- `activate_atomic_control(profile_name) -> bool`

### 2.6 拟人化输入
- `humanized_click(x, y, button=1) -> bool`
- `humanized_input(text) -> bool`

## 3. ATSPIEngine 主要 API（Python 绑定）

### 3.1 基础
- `initialize() -> bool`
- `get_wechat_application() -> AtspiAccessible*`
- `get_all_controls(root) -> list[AtspiAccessible*]`
- `find_controls_by_role(root, role) -> list[AtspiAccessible*]`
- `find_controls_by_name(root, name) -> list[AtspiAccessible*]`
- `click_control(control) -> bool`
- `input_text(control, text) -> bool`
- `get_control_region(control) -> Region`
- `get_control_text(control) -> str`
- `get_control_name(control) -> str`
- `get_control_role(control) -> str`

### 3.2 快照与遍历
- `capture_tree_snapshot(max_nodes=800, max_depth=-1, include_text=True, deduplicate=False) -> list[dict]`
- `get_ui_elements(max_nodes=300) -> list[dict]`
- `traverse_control_tree(max_nodes=800, max_depth=-1) -> list[dict]`

## 4. 其他核心类职责
- `WindowManager`：窗口查找、激活、窗口信息、搜索。
- `ImageProcessor`：图像增强、裁剪、边缘/区域处理（当前绑定仅暴露构造）。
- `OCRAEngine`：文本识别与候选提取。
- `HumanizationEngine`：拟人化延迟、输入节奏与随机偏移。

## 5. 关键数据结构（Python 侧）
- `WindowInfo`：`id/title/x/y/width/height/is_active`
- `Region`：`x/y/width/height`
- `Message`：`id/sender/content/confidence`
- `Contact`：`id/name/wechat_id/avatar`
- AT-SPI 快照：`list[dict]`（字段来自树快照序列化）

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
- `install_deps.sh` / `install_atspi.sh` / `install_ydotool.sh`：环境准备。

## 7. 与后端 API 的封装关系
- C++ 模块由 Python 绑定导出，后端通过 `backend/api/v1/rpa*.py` 调用。
- 扫描、构建、标注确认等框架能力在后端路由层完成组合封包。
- 建议上层统一走后端 API，不直接跨层耦合底层引擎细节。

## 8. 稳定性与独立化要求
1. 保留多层降级策略（AT-SPI -> 几何/坐标 -> 键盘/OCR）。
2. 保留诊断信息输出（策略、耗时、节点数量、错误原因）。
3. 保持 `include/src/bindings/examples` 结构稳定。
4. API 文档与构建/测试脚本同步更新。

## 9. 更新记录
- 2026-02-26：按当前 bindings 与头文件更新 API 清单（原子控件/拟人化/截图注解等）。
