# 微信自动化 C++ 底层重构总体框架（AT-SPI 原子控件化）

更新时间：2026-02-26

## 1. 重构目标（与你当前诉求对齐）

- 以 C++ 作为微信自动化底层主执行引擎（激活/定位/点击/输入/读取）。
- 把 AT-SPI 从“查找脚本”升级为“原子控件运行时平台”。
- 聊天记录、弹窗、联系人等统一抽象为“原子容器（Atomic Container）”。
- 前端可直接管理控件与动作包，微信改版后可快速重建与刷新定位。
- 形成稳定、高效、可扩展、可复用的跨层架构。

---

## 2. 现状评估（基于当前代码）

### 2.1 已具备能力（可复用）

- C++ 已有统一树抓取与筛选：
  - `ATSPIEngine.capture_tree_snapshot`、`query_nodes`、`build_atomic_containers`
- C++ 已有原子能力入口：
  - `WeChatManager.query_atomic_controls`
  - `get_atomic_container_by_profile`
  - `refresh_atomic_profile`
  - `find_chat_atomic_groups`
  - `detect_popup_atomic_controls`
  - `click_atomic_control` / `input_text_atomic_control` / `activate_atomic_control`
- 后端已有原子接口：
  - `/api/v1/rpa/atomic/profiles`
  - `/api/v1/rpa/atomic/profile/refresh`
  - `/api/v1/rpa/atomic/chat/discover`
  - `/api/v1/rpa/atomic/popup/discover`
- 前端 API 已有对应封装：
  - `listAtomicProfiles`、`refreshAtomicProfile`
  - `discoverChatAtomicGroups`、`discoverPopupAtomicControls`
- 已存在 profile 配置：
  - `cpp_rpa/config/atspi_atomic_profiles.ini`

### 2.2 当前主要缺口（必须补）

1. C++ 动作接口还偏“单次查找+执行”，缺少统一 Action Runtime（重试、回退、验证）。
2. 原子容器已有基础分组，但缺少标准化容器类型协议（chat/popup/contact/search）。
3. 聊天“原子消息对象”未形成稳定契约（消息方向、时间、内容块、多元素关联）。
4. 仍存在 Python/后端历史兼容路径和动作逻辑分散，跨层语义没有完全统一。
5. 前端动作包页已能消费控件库，但缺少“改版后一键重建+差异对比+批量替换 control_uid”。
6. 缺少事件增量机制（focus/state/children-changed），大多仍靠轮询快照。

---

## 3. 目标架构（建议最终形态）

## 3.1 五层模型

1. **L0 系统适配层（C++）**
   - ATSPI、窗口管理、输入设备、截图/OCR回退。

2. **L1 原子能力层（C++）**
   - `NodeCapture`：抓树/增量。
   - `NodeQuery`：多特征筛选。
   - `NodeAction`：激活/点击/输入/读取。

3. **L2 原子容器层（C++）**
   - `AtomicContainerBuilder`：chat/popup/contact 容器构建。
   - `AtomicProfileEngine`：profile 解析、评分、重建建议。

4. **L3 编排服务层（Python/FastAPI）**
   - API 合同、任务编排、状态机、动作包执行、日志与回放。

5. **L4 前端管理层（Vue）**
   - 控件库管理、容器可视化、重建建议应用、动作包编辑与验证。

---

## 4. C++ 重构主干（优先级最高）

## 4.1 新增核心类（保持现有类兼容）

- `AtomicFeatureExtractor`
  - 从节点提取稳定特征：`role/name/text/state/path/depth/ratio/neighbor`
- `AtomicMatcher`
  - 统一匹配评分：语义 > 状态 > 层级 > 几何
- `AtomicContainerBuilderV2`
  - 输出标准容器：`chat_group/popup_menu/contact_list/search_panel`
- `AtomicActionExecutor`
  - 统一执行链：`precheck -> action -> postcheck -> fallback`
- `AtomicRebuilder`
  - 生成重建建议与候选替换（支持 profile 热更新）

## 4.2 动作统一接口（C++ First）

建议在 `WeChatManager` 增加统一动作入口：

- `execute_atomic_action(action_spec: map) -> result`
- 支持动作类型：
  - `activate`
  - `focus`
  - `click`
  - `input_text`
  - `read_text`
  - `scroll`
  - `open_popup`
  - `select_menu_item`

动作返回统一结果：

- `success`
- `used_strategy`（atspi_direct / atspi_action / xdotool_fallback）
- `latency_ms`
- `matched_node`
- `post_check`
- `error_code`

## 4.3 查找与重建策略升级（重点）

从“单条件查找”升级为“分层评分匹配”：

- 一级：`role + state`（必需）
- 二级：`name/text 正则`（可选）
- 三级：`parent_role + parent_path`（结构约束）
- 四级：`x/y ratio`（布局约束）
- 五级：`neighbor anchors`（发送按钮邻居、输入框邻接）

输出候选分值 `match_score`，并保留 Top-K 供前端选择。

---

## 5. 原子容器标准（解决聊天与弹窗复用）

## 5.1 原子节点标准字段（统一前后端）

- 基础：`node_id/index/depth/path/parent_path/sibling_index`
- 语义：`role/name/text/parent_role`
- 状态：`visible/showing/editable/focusable/sensitive`
- 几何：`x/y/width/height/center_x/center_y/x_ratio/y_ratio`
- 匹配：`profile_name/match_score/matched_rules`

## 5.2 原子容器标准字段

- `container_id`
- `container_type`（`chat_group`/`popup_menu`/`contact_group`/`search_panel`）
- `container_key`
- `version`
- `anchor_features`
- `items[]`

## 5.3 聊天消息原子对象（关键）

每条消息建议拆分为：

- `message_id`
- `direction`（self/other/system）
- `sender`
- `time_text`
- `content_blocks[]`（text/image/file/link）
- `message_bounds`
- `source_nodes[]`

这样微信 UI 改版时只需重建 `content_blocks` 规则，不改上层动作包。

---

## 6. 后端编排改造（承上启下）

## 6.1 API 分组建议

保留现有接口并新增 V2：

- `/api/v1/rpa/atomic/*`（现有）
- `/api/v1/rpa/atomic/v2/query`
- `/api/v1/rpa/atomic/v2/containers/discover`
- `/api/v1/rpa/atomic/v2/action/execute`
- `/api/v1/rpa/atomic/v2/profile/rebuild`
- `/api/v1/rpa/atomic/v2/tree/delta`

## 6.2 服务边界建议

- `backend/core/atspi_tree_service.py` 继续做树采集与筛选归一。
- 新增 `backend/core/atomic_runtime_service.py`：
  - 容器发现
  - 动作执行编排
  - post-check 与回退策略

## 6.3 动作包执行与原子控件打通

在 `rpa_definition` 的执行链中，统一支持：

- `control_uid -> atomic profile -> dynamic re-locate`
- 控件失效时自动触发 `profile refresh/rebuild suggest`
- 执行日志写入 `used_profile/match_score/fallback_reason`

---

## 7. 前端重构重点（提高改版恢复速度）

## 7.1 新增“原子控件中心”页（建议）

仅需最小功能，不做复杂 UI：

- profile 列表 + 命中统计
- 一键刷新建议（显示差异）
- 应用建议（写回配置/数据库）
- 容器预览（chat/popup/contact）

## 7.2 与操作打包页联动

在 `WeChatOperationPackages` 增加两项：

- `重新定位 control_uid`（按 profile 与特征自动替换）
- `批量校验动作包`（输出失效步骤清单）

---

## 8. 三阶段落地计划（可直接执行）

## Phase 1（1~1.5 周）稳定基线

- C++：落地 `AtomicActionExecutor` 基础版（click/input/activate/read）。
- 后端：新增 `/atomic/v2/action/execute`。
- 前端：操作打包页接入执行返回的 `used_strategy/match_score`。
- 验收：发送消息与点击菜单成功率 > 95%。

## Phase 2（1~1.5 周）容器化与重建

- C++：`AtomicContainerBuilderV2` + `AtomicRebuilder`。
- 后端：新增 `/containers/discover` 与 `/profile/rebuild`。
- 前端：新增“原子控件中心”最小页。
- 验收：微信小改版后 30 分钟内恢复核心流程。

## Phase 3（1~2 周）增量刷新与性能

- C++：接入 ATSPI 事件订阅（focus/state/children-changed）。
- 后端：新增 `/tree/delta`。
- 前端：支持增量刷新容器，不全量重拉。
- 验收：树抓取 p95 < 300ms，动作执行 p95 < 500ms（ATSPI主路径）。

---

## 9. 稳定性与性能基线（必须量化）

- `atomic_query_latency_ms`（p50/p95）
- `action_success_rate`（按 action_type）
- `fallback_rate`（越低越好）
- `container_rebuild_time_ms`
- `profile_hit_rate`
- `invalid_control_uid_count`

每个动作都应落日志：`run_id/package_id/action_key/profile_name/match_score/used_strategy`。

---

## 10. 风险与控制

- 风险1：微信频繁改版导致规则漂移。
  - 控制：profile 配置驱动 + rebuild suggestion + Top-K 候选。
- 风险2：ATSPI 临时不可用。
  - 控制：C++ 内建 xdotool/几何兜底，后端显式返回 `fallback_used=true`。
- 风险3：多层重复逻辑。
  - 控制：查找与执行统一收口到 C++，后端只编排。

---

## 11. 立即可执行任务清单（建议本周）

1. 在 C++ 增加 `execute_atomic_action` 与统一返回结构。
2. 把 `click_atomic_control/input_text_atomic_control/activate_atomic_control` 改为调用统一执行器。
3. 后端新增 `/api/v1/rpa/atomic/v2/action/execute`。
4. 在操作打包执行结果中记录 `match_score/used_strategy`。
5. 前端动作包页增加“失效控件重定位”按钮（最小可用）。

---

## 12. 结论

你的项目已经有很好的原子化基础（C++ 查询、profile、容器发现、前端动作包联动）；本次重构不需要推倒重来，正确路径是：

- **以 C++ 为唯一底层执行真源**
- **以 profile + 容器为中间抽象**
- **以前端动作包为业务复用出口**

按上述三阶段推进，可以把微信自动化从“可用”升级到“可维护、可重建、可扩展”的工程化状态。