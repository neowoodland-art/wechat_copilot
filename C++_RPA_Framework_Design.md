# C++ RPA 框架设计文档（cpp_rpa）

## 1. 定位
`cpp_rpa` 是微信自动化的 C++ 核心层，负责高性能和高稳定性的桌面交互能力，通过 `pybind11` 暴露给 Python 服务层。

## 2. 分层架构

### 2.1 系统交互层
- X11/窗口工具链：`xdotool`、`wmctrl`。
- 可访问性能力：AT-SPI。

### 2.2 核心引擎层
- `WindowManager`：窗口生命周期控制。
- `ATSPIEngine`：控件树检索与控件交互。
- `ImageProcessor`：图像预处理与区域操作。
- `OCREngine`：图像文本识别。
- `HumanizationEngine`：拟人化操作策略。

### 2.3 业务编排层
- `WeChatManager`：统一整合上面各引擎，对外提供稳定业务 API。

### 2.4 绑定层
- `bindings/python_bindings.cpp`：通过 pybind11 向 Python 输出统一接口。

## 3. 目录结构与职责
- `include/`：头文件与接口声明。
- `src/`：核心实现代码。
- `bindings/`：Python 绑定。
- `examples/`：调用示例。
- `test_*.py`：核心能力测试脚本。
- `build*.sh`：构建与修复脚本。

## 4. 模块职责清单

### 4.1 WeChatManager
- 微信窗口激活、状态识别、截图、元素检测、消息动作。
- 上层只依赖此类可减少耦合与变更面。

### 4.2 ATSPIEngine
- 控件树遍历、控件命中、点击/输入。
- 提供树快照与调试能力，支持上层可观测诊断。

### 4.3 ImageProcessor + OCREngine
- 识别链路中的图像增强、区域定位、文本提取。

### 4.4 HumanizationEngine
- 延迟、偏移、输入节奏随机化，降低行为特征风险。

### 4.5 WindowManager
- 窗口定位、几何控制、激活与命令执行。

## 5. 启动、构建、测试链路

### 5.1 构建
```bash
cd cpp_rpa
./build.sh
# 异常时
./build_fixed.sh
```

### 5.2 重建
```bash
./rebuild.sh
```

### 5.3 测试
```bash
python test_wechat_window.py
python test_atspi.py
python test_cpp_atspi_only.py
python test_humanization.py
python simple_test.py
```

## 6. 与后端封包层协同
- 后端路由负责“流程封包”和“任务级状态机”。
- C++ 层负责“能力原子化”和“可重复调用稳定性”。
- 通过这种分工，上层可实现：
  - 扫描任务异步化
  - 进度与取消
  - 区域范围约束
  - 结果确认图生成

## 7. 当前框架完成状态
- 系统交互层：✅
- 核心引擎层：✅
- 业务编排层：✅
- 绑定层：✅
- 稳定性回归体系：🔄 持续优化

## 8. 独立项目化准备
1. 保持 API 稳定入口（`WeChatManager`）。
2. 保持脚本化构建与测试入口稳定。
3. 输出统一 API 文档与框架文档。
4. 高风险能力必须保留降级策略与诊断字段。
5. 后续拆分时，优先迁移 `cpp_rpa` + 文档 + 脚本三件套。

## 9. 2026-02-22 变更说明
- 与上层“扫描可中断、进度可观测、区域约束优先、确认图闭环”框架完成对齐。
- 文档整理为独立项目可直接继承的框架版说明。
