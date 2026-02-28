# 微信自动化底层重构框架（AT-SPI 原子化 V2）

## 目标
- 统一底层能力：激活、定位、点击、输入、读取、弹窗菜单处理。
- 原子控件可重建：微信界面改版后可通过“重建建议”快速更新 profile。
- 容器可组合：聊天记录、弹窗菜单、联系人列表都转为可复用“原子容器”。
- 前端可管理：配置列表、容器发现、重建参数由 API 直接驱动。

## 分层架构
1. **C++ ATSPI 能力层（`ATSPIEngine`）**
   - 树抓取：`capture_tree_snapshot` / `capture_tree_nodes`
   - 语义筛选：`query_nodes`（role/name/text/path/depth/state/ratio）
   - 容器构建：`build_atomic_containers`

2. **C++ 编排层（`WeChatManager`）**
   - 既有：`query_atomic_controls` / `get_atomic_container_by_profile`
   - 新增：
     - `list_atomic_profiles()`
     - `refresh_atomic_profile(profile_name)`
     - `find_chat_atomic_groups()`
     - `detect_popup_atomic_controls()`
   - 作用：把“复杂树分析”转成前端可直接消费的数据。

3. **Profile 配置层（`cpp_rpa/config/atspi_atomic_profiles.ini`）**
   - 原子规则由配置驱动，不改代码即可适配新版微信。
   - 关键维度：`role/depth/state/path/ratio`。

4. **后端 API 层（`backend/api/v1/rpa_control.py`）**
   - 新增：
     - `GET /api/v1/rpa/atomic/profiles`
     - `POST /api/v1/rpa/atomic/profile/refresh`
     - `POST /api/v1/rpa/atomic/chat/discover`
     - `POST /api/v1/rpa/atomic/popup/discover`

5. **前端 RPA 管理层（`frontend/src/api/index.js`）**
   - 新增 API 包装：
     - `listAtomicProfiles`
     - `refreshAtomicProfile`
     - `discoverChatAtomicGroups`
     - `discoverPopupAtomicControls`

## 核心流程
### A. 控件改版后的快速恢复
1. 前端拉取 `listAtomicProfiles`。
2. 对关键 profile（如 `chat_input_box`、`chat_send_button`）调用 `refreshAtomicProfile`。
3. 将返回建议（`expected_depth/min|max_x|y_ratio/role`）写回配置。
4. 用 `query_atomic_controls` 验证命中率。

### B. 聊天容器重建
1. 调用 `discoverChatAtomicGroups`。
2. 按 `container_key/container_index/item_index` 聚合为消息组。
3. 前端将消息组映射到“聊天原子容器”，供 SOP 和操作打包复用。

### C. 弹窗自动识别
1. 触发右键/操作后调用 `discoverPopupAtomicControls`。
2. 返回菜单项列表（按坐标排序），再按名称或正则选择目标动作（如“转文字/保存”）。

## 数据契约（建议）
- 原子节点字段：`name role text x y width height depth path parent_path visible showing editable focusable sensitive`
- 容器扩展字段：`container_key container_index item_index container_size container_type`
- 重建建议字段：`role_equals expected_depth min_depth max_depth min|max_x|y_ratio sample_count`

## 落地建议（两周）
- 第 1 周：接入新 API + 前端配置页（列表、建议预览、应用更新）。
- 第 2 周：把“发送消息/读取聊天/处理弹窗”迁移为 profile + 容器驱动。

## 稳定性策略
- 优先语义特征（role + state + parent_path），深度只做辅助。
- 坐标比例使用窗口相对值，避免分辨率和窗口尺寸变化影响。
- 对关键动作保留拟人化点击/输入作为系统级兜底。
