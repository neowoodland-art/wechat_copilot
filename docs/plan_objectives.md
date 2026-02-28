完善调整计划表（更新版）
阶段1：框架对齐与代码分析（1-2天）
1.1 现有代码能力盘点
ui_profile API：已有 fix_window、full_scan、build、get、list 接口，支持窗口固定、扫描、配置构建。
UI分析器：ui_analyzer.py 支持元素分析，ui_analysis.py 提供REST接口。
鼠标扫描：rpa_compatibility.py 中已有 _collect_mouse_scan_layer_real 函数，支持悬浮变色检测。
数据存储：ui_analysis_profiles.json 存储配置。
1.2 新框架差异识别
5区域定义：现有代码无明确区域划分，需要扩展为搜索栏、主菜单工具栏、联系人列表、聊天信息展示、聊天输入发送。
两套模板：现有profile为通用结构，需要按"聊天界面"和"联系人界面"分类存储。
标注流程：现有full_scan为基础，但缺少按区域顺序标注、空格截图、ESC结束的交互流程。
模板输出：需要扩展profile结构，包含基准图、区域边界、可点击控件坐标、截图库。
1.3 调整范围确认
后端：扩展 rpa_compatibility.py 中的ui_profile接口。
前端：更新 LayoutSetup.vue 和 RPATest.vue，添加区域标注UI。
数据：扩展profile JSON结构，支持5区域和两套模板。
阶段2：后端API扩展（2-3天）
2.1 扩展FullScanRequest模型

class FullScanRequest(BaseModel):    profile_name: str = "default"    template_type: str = "chat"  # "chat" 或 "contacts"    timeout_seconds: int = 45    include_mouse_scan: bool = True    include_control_layer: bool = True    persist_as_baseline: bool = True    use_real_mouse_scan: bool = True    scan_direction: str = "right_to_left"    scan_step_x: int = 80    scan_step_y: int = 70    scan_settle_ms: int = 120    scan_max_points: int = 180    scan_diff_threshold: int = 24    scan_min_contour_area: int = 160    scan_min_stable_hits: int = 3    scan_overlay_alpha: float = 0.28
2.2 实现5区域预定义
在 rpa_compatibility.py 中添加区域定义：


PREDEFINED_REGIONS = {    "search_bar": {"name": "搜索栏区域", "function": "search_contacts"},    "main_menu": {"name": "主菜单工具栏区域", "function": "switch_templates"},    "contact_list": {"name": "联系人列表区域", "function": "select_contacts"},    "chat_display": {"name": "聊天信息展示区域", "function": "view_messages"},    "chat_input": {"name": "聊天输入发送区域", "function": "input_messages"}}
2.3 扩展full_scan接口
添加 template_type 参数，按聊天/联系人界面分类存储。
在扫描结果中预标注5个区域边界（基于窗口尺寸比例估算）。
支持区域顺序：搜索栏 → 主菜单 → 联系人列表 → 聊天展示 → 聊天输入。
2.4 新增区域标注接口

@router.post("/wechat/ui_profile/annotate_region")async def annotate_region(request: AnnotateRegionRequest):    # 支持单个区域的标注提交    # 接收区域ID、边界坐标、手动调整
2.5 扩展BuildProfileRequest

class RegionAnnotation(BaseModel):    region_id: str  # 如 "search_bar", "main_menu" 等    function: str    name: Optional[str] = None    clickable: bool = True    needs_rescan_after_click: bool = False    control_type: Optional[str] = None    bounds: Optional[Dict[str, int]] = None    confidence: float = 1.0    notes: Optional[str] = None
2.6 实现模板切换接口

@router.post("/wechat/ui_profile/switch_template")async def switch_template(template_type: str):  # "chat" 或 "contacts"    # 模拟点击主菜单的聊天/联系人按钮    # 切换到指定模板界面
阶段3：前端界面调整（2-3天）
3.1 更新LayoutSetup.vue
添加模板类型选择：聊天界面 / 联系人界面。
实现5区域顺序标注流程：
显示当前区域名称和边界框。
支持手动调整区域边界。
集成鼠标扫描结果，自动填充可点击控件。
添加基准图显示和区域覆盖层。
3.2 扩展RPATest.vue
添加"自动化标注"模式：
窗口固定后，显示标注指导。
集成空格键截图功能（需后端支持键盘监听）。
区域完成提示和ESC结束确认。
显示标注进度：5/5区域，当前区域控件数量。
3.3 新增标注专用组件
创建 UIAnnotation.vue：

基准图画布，支持绘制区域边界。
控件点位可视化，悬浮显示信息。
截图库预览，展示变化区域。
3.4 模板管理界面
列出聊天模板和联系人模板。
支持模板导出/导入。
显示模板完成状态和控件统计。
阶段4：数据结构扩展（1天）
4.1 扩展profile JSON结构

{  "version": "2.0",  "template_type": "chat",  // "chat" 或 "contacts"  "baseline_image": "base64_data",  "regions": {    "search_bar": {      "name": "搜索栏区域",      "bounds": {"x": 0, "y": 0, "width": 400, "height": 50},      "function": "search_contacts",      "controls": [...]    },    "main_menu": {...},    "contact_list": {...},    "chat_display": {...},    "chat_input": {...}  },  "special_controls": {    "scrollbars": [...],    "dropdowns": [...]  },  "screenshots": {    "control_hover_001": "base64_data",    ...  }}
4.2 迁移现有profile
为现有profile添加 template_type 字段。
自动识别并分配到5区域（基于坐标位置）。
阶段5：标注流程实现（3-4天）
5.1 实现键盘监听（后端）
在full_scan过程中监听空格键和ESC键。
空格键触发：截取当前变化区域，保存到截图库。
ESC键触发：结束当前区域标注，进入下一区域。
5.2 区域顺序控制
强制按预定义顺序标注：搜索栏 → 主菜单 → 联系人列表 → 聊天展示 → 聊天输入。
完成后标注特殊控件：下拉框、滚动条等。
5.3 模板独立性保证
聊天模板和联系人模板完全独立存储。
切换模板时清除当前标注状态。
防止跨模板操作导致界面跳转。
5.4 基准图与变化图管理
基准图：窗口固定后的首次截图。
变化图：鼠标悬浮后的差异区域截图。
自动剔除鼠标光标（基于尺寸和位置过滤）。
5.5 元素标注多层流程实现（新增）
第一层：AT-SPI辅助树标注

调用 get_atspi_tree_snapshot 获取控件树结构。
分析节点位置、名称、角色，确保无位置冲突或遗漏。
自动标注可点击控件（按钮、输入框等），记录边界坐标。
过滤噪声节点（如静态文本），确认标注准确性。
第二层：鼠标移动截图标注

在AT-SPI标注基础上，进行鼠标悬浮扫描。
鼠标移动到控件上方，检测变色/高亮变化。
按空格键截取变化区域，自动剔除鼠标光标。
记录悬浮截图和控件边界，补充AT-SPI可能遗漏的动态元素。
第三层：OCR+大模型识别标注

对截图区域进行OCR文本识别，提取控件标签和内容。
调用AI大模型（如GPT）分析控件功能和上下文。
结合OCR结果和大模型推理，智能标注控件类型（按钮、输入框、列表等）。
生成控件描述和功能推断，提升标注智能化。
第四层：多层结合与人工确认

融合AT-SPI、鼠标扫描、OCR+AI的结果，去除冲突和重复。
在前端界面分析预览中显示标注结果，支持人工调整边界和类型。
用户确认后保存到profile，生成最终可复用配置。
预览界面支持缩放、对比基准图，验证标注完整性。
阶段6：测试与验证（2-3天）
6.1 单元测试
测试5区域边界计算。
验证模板切换逻辑。
检查profile数据完整性。
6.2 集成测试
完整标注流程：窗口固定 → 基准图 → 5区域标注 → 特殊控件 → 保存模板。
模板加载和应用测试。
跨模板切换验证。
6.3 界面分析完成后元素测试（新增）
元素位置操作测试：

加载标注完成的profile，验证各控件坐标准确性。
模拟点击各区域控件，检查位置是否正确触发操作。
测试边界情况：控件边缘点击、区域重叠处理。
记录操作成功率和偏差统计。
控件输入测试：

对输入框控件测试文本输入功能（AT-SPI输入 + 键盘模拟）。
验证发送按钮、搜索框等交互控件响应。
测试特殊控件：下拉框展开、滚动条滑动、弹窗操作。
评估输入延迟和成功率，确保拟人化效果。
端到端联调测试：

完整流程：标注 → 保存 → 加载 → 操作测试。
跨模板一致性验证（聊天界面和联系人界面）。
异常处理测试：控件不可用、位置变化等。
6.4 用户验收
前端标注界面可用性测试。
标注结果准确性验证。
模板复用效果评估。
阶段7：文档更新（1天）
7.1 更新README.md
添加新框架说明和使用流程。
更新API文档，包含新接口。
7.2 更新edit.md
记录调整过程和关键决策。
按小时记录开发进展。
7.3 创建使用指南
详细标注操作步骤。
模板管理和应用说明。
预期成果
两套完整模板：聊天界面和联系人界面，各包含5区域定义和控件标注。
自动化标注流程：支持键盘交互的半自动化标注。
可复用配置：结构化存储，便于脚本复用和坐标复用。
扩展API：后端支持新框架的所有功能。
用户友好界面：前端提供直观的标注工具。
风险与应对
鼠标扫描准确性：通过参数调优和后处理过滤提升。
区域边界识别：结合比例估算和手动调整。
模板一致性：严格按框架规则，避免跨模板操作。
