# ATSPI树抓取重构说明（2026-02-23）

## 背景问题
现有 ATSPI 树抓取链路存在以下结构性问题：

- C++、pybind、后端路由各自实现一套遍历逻辑，行为不一致。
- 树快照与平铺快照混用，字段规范不统一（`path/depth/parent_index` 易丢失）。
- 失败回退策略分散在多个层级，难以定位“数据少/数据偏移/抓取慢”的根因。
- 路由内嵌大量拼接式逻辑，维护成本高、回归风险高。

## 本次重构目标

- **单一事实来源**：树抓取逻辑统一到 C++ `ATSPIEngine`。
- **统一数据模型**：统一输出 `index/depth/parent_index/path/name/role/text/bounds`。
- **可控采样策略**：统一 `max_nodes/max_depth/deduplicate/include_text` 参数。
- **上层瘦身**：FastAPI 路由只负责参数接入，业务编排交给服务模块。

## 已落地改动

### 1) C++ 核心层（统一抓取内核）

- 文件：`cpp_rpa/include/atspi_engine.h`
  - 新增统一接口：`capture_tree_snapshot(...)`。

- 文件：`cpp_rpa/src/atspi_engine.cpp`
  - `get_all_controls` 改为迭代式遍历，避免递归链路不稳定。
  - 新增 `capture_tree_snapshot`：
    - 迭代 DFS 抓取，支持深度限制。
    - 输出标准字段：`index/depth/parent_index/sibling_index/path/name/role/text/x/y/width/height`。
    - 统一资源释放策略（子节点处理后释放，root 由调用方管理）。

### 2) 管理层（WeChatManager）

- 文件：`cpp_rpa/src/wechat_manager.cpp`
  - `get_atspi_control_snapshot` 与 `get_atspi_tree_snapshot` 统一改为调用 `atspi_engine_.capture_tree_snapshot(...)`。
  - 删除重复遍历拼装代码，保证两者语义一致、参数可控。

### 3) Python 绑定层（pybind11）

- 文件：`cpp_rpa/bindings/python_bindings.cpp`
  - 新增 `ATSPIEngine.capture_tree_snapshot(max_nodes, max_depth, include_text, deduplicate)`。
  - `get_ui_elements`、`traverse_control_tree` 改为转调统一接口。
  - 删除绑定层内联树遍历大段逻辑，避免再次分叉。

### 4) 后端服务层（FastAPI）

- 新增文件：`backend/core/atspi_tree_service.py`
  - 统一承载：多轮抓取、树/平铺回退、归一化、关键字过滤、去重、排序、导出。

- 文件：`backend/api/v1/rpa_compatibility.py`
  - `POST /rpa/atspi/tree_snapshot` 路由改为调用 `build_snapshot_payload(...)`。
  - 路由从“巨型内联逻辑”收敛为“参数透传 + 结果返回”，便于后续迭代。

## 当前能力边界

- 目前仍是“全量快照 + 策略筛选”模式；尚未引入真正的事件驱动增量树（AT-SPI event cache）。
- 若需要更强实时性，可在下一阶段加入：
  - 事件订阅（focus/name/state/children-changed）
  - 增量 patch 输出（insert/update/remove）
  - 热点子树优先刷新（输入框、会话列表、消息区）

## 下一阶段建议（可直接排期）

1. 在 C++ 引入 AT-SPI 事件总线与节点缓存，提供 `get_incremental_snapshot(since_version)`。
2. 后端新增 `/rpa/atspi/tree_delta`，前端按 patch 应用，降低带宽与延迟。
3. 增加稳定性指标：抓取耗时 p95、有效节点率、重复率、坐标命中率。
4. 补一组回归用例：微信主窗口、聊天窗口、联系人搜索窗口三类场景。
