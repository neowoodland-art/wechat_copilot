# C++ RPA 基于 AT-SPI 的整体重构框架（V1）

## 目标

- 用 AT-SPI 替换鼠标扫描主链路，统一激活、查找、点击、输入、菜单处理。
- 引入“原子控件 + 原子容器”模型，支持聊天记录打包、客户档案提取、动作复用。
- 配置优先：微信升级后主要通过 `config/atspi_atomic_profiles.ini` 调参适配。

## 分层架构

1. **ATSPIEngine（底层能力层）**
   - 负责树快照、节点状态提取、组合过滤（role/name/depth/state/path/ratio）。
   - 新增：`capture_tree_nodes`、`query_nodes`、`build_atomic_containers`。

2. **Atomic Profile（规则配置层）**
   - 文件：`config/atspi_atomic_profiles.ini`。
   - 用 profile 定义控件/容器的筛选参数：
     - 角色、深度、名称内容、状态位（visible/showing/editable/focusable）
     - 坐标比例（min/max x/y ratio）
     - 可选人机化延迟参数（pre/post click/input）。

3. **WeChatManager（编排执行层）**
   - 新增：
     - `query_atomic_controls(filters)`
     - `get_atomic_container_by_profile(profile_name, group_by)`
     - `click_atomic_control(profile_name)`
     - `input_text_atomic_control(profile_name, text)`
     - `activate_atomic_control(profile_name)`
   - `scan_interface_by_mouse` 入口已改为 AT-SPI 扫描（保留原函数名，兼容现有调用）。

4. **Python/后端调用层**
   - Python 绑定已暴露上述新接口。
   - 后端可直接用 profile 名称驱动，不再硬编码坐标和深度。

## 原子模型

- **原子控件**：一个可直接操作节点（可点击/可输入/可读取）
  - 示例：发送按钮、聊天输入框、弹出菜单项。

- **原子容器**：同源节点集合（按 `parent_path` 或 `depth_role` 分组）
  - 示例：聊天记录容器、联系人列表容器。
  - 用于批量提取并转结构化对象（历史记录、客户档案等）。

## 已预置 profile（可直接用）

- `menu_bar_buttons`：深度 6 菜单功能按钮。
- `chat_send_button`：深度 15 且名称包含“发送”。
- `chat_action_buttons`：深度 16 聊天区域功能按钮。
- `chat_input_box`：可编辑可聚焦文本输入框。
- `chat_message_items` / `chat_message_texts`：聊天记录容器节点。
- `popup_menu_items`：弹出菜单项。
- `contact_list_items`、`search_box`。

## 拟人化策略

- 点击/输入均支持 profile 中配置延迟：
  - `pre_click_delay_ms` / `post_click_delay_ms`
  - `pre_input_delay_ms` / `post_input_delay_ms`
- 继续沿用 `HumanizationEngine` 的抖动与随机停顿。

## 下一步落地顺序（建议）

1. 后端 API 切换到 profile 驱动（发送消息、读取聊天容器、弹出菜单操作）。
2. 前端增加 profile 编辑器（读取/更新 ini），实现“参数即能力更新”。
3. 增加容器解析器：把 `chat_message_items` 转标准消息 DTO（sender/content/time/type）。
4. 增加菜单动作模板：右键消息 -> 菜单过滤 -> 点击“转文字/保存”。
5. 建立版本基线：每次微信升级后导出树快照并对比 profile 命中率。
