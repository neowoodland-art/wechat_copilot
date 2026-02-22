# 项目开发日志（按小时）

> 记录规则：本文件记录“开发过程 + 问题 + 修改 + 测试结果”，时间戳按小时。

## 2026-02-22

### 09:00 - 鼠标扫描可中断与进度化改造（后端）
- 目标：避免扫描过程中鼠标意外移动导致整轮无效，提供可中断与可观测进度。
- 修改文件：`backend/api/v1/rpa_compatibility.py`
- 新增能力：
  - 扫描任务异步化（任务状态内存管理）。
  - 新增任务接口：
    - `POST /api/v1/rpa/wechat/ui_profile/full_scan_async/start`
    - `GET /api/v1/rpa/wechat/ui_profile/full_scan_async/status`
    - `POST /api/v1/rpa/wechat/ui_profile/full_scan_async/cancel`
  - 扫描过程支持取消信号检测（扫描点循环、区域循环、动作点前后均检查）。
  - 扫描过程分阶段进度回传（prepare/mouse_scan/control_layer/geometry/persist/done）。
- 结果：扫描可中断，状态可轮询，前端可以实时显示百分比与阶段说明。

### 10:00 - 鼠标扫描进度与中断按钮（前端）
- 修改文件：`frontend/src/views/RPATest.vue`
- 改动点：
  - “全面扫描”改为异步任务模式，新增轮询逻辑。
  - 新增中断按钮 `cancelFullScan`。
  - 新增状态字段：任务ID、运行中标记、进度百分比、阶段、说明。
  - 新增进度条 UI，扫描中可见阶段与百分比。
- 结果：可在扫描中主动中断，避免错误采样继续污染结果。

### 11:00 - 扫描后构建确认图闭环
- 目标：扫描并构建后，必须有“标注好截图”供人工确认。
- 修改：
  - 后端新增 `GET /api/v1/rpa/wechat/ui_profile/annotated_preview`。
  - 前端 `runBuildProfile` 成功后自动请求预览图并展示“构建后标注确认图”。
- 结果：形成“扫描 -> 标注 -> 构建 -> 截图确认”的可视闭环。

### 12:00 - 区域范围未生效问题修复
- 问题：扫描未稳定使用前面配置的区域范围，导致识别偏移。
- 根因：profile 名称与模板后缀不一致时，后端可能回退到估算区域。
- 修复：
  - 后端区域加载增加模板化回退顺序：
    - 先查 `profile_name`
    - 再查 `profile_name_chat/profile_name_contacts`
    - 再查 `default_chat/default_contacts`
  - 前端扫描与构建统一使用模板化配置名（自动拼 `_chat` 或 `_contacts`）。
  - 前端调用 full scan 时显式传 `template_type`。
- 结果：扫描优先命中已保存区域边界，不再默认漂移到估算范围。

### 13:00 - 差分计算“未出控件”调试增强
- 问题：移动鼠标后与基准图差分结果不稳定，偶发“无控件候选”。
- 修复：
  - 后端在 `mouse_scan_meta` 增加 `region_debug`（每区域扫描点数、候选前后数量、是否有效边界）。
  - 前端新增“区域调试”显示，快速判断是：
    1) 该区没扫描点；
    2) 扫描了但候选被过滤；
    3) 区域边界本身无效。
- 结果：差分问题从“黑盒”变为“可定位”。

### 14:00 - 代码自检
- 检查文件：
  - `backend/api/v1/rpa_compatibility.py`
  - `frontend/src/views/RPATest.vue`
- 自检结果：无语法/静态错误。

### 15:00 - 文档体系同步（本轮）
- 按职责更新：`tree.md`、`edit.md`、`README.md`、`INSTALL.md`、`ProjectFramework.md`、`# C++ RPA模块API参考文档.md`、`C++_RPA_Framework_Design.md`。
- 文档策略：
  - `edit.md` 小时粒度（详细过程与问题）；
  - `README.md` 天粒度（精简摘要）；
  - `ProjectFramework.md` 仅更新大框架状态，不扩增框架条目。

---

## 2026-02-21

### 10:00 - 全项目目录重扫与文档基线校验
- 全量重扫目录并更新 `tree.md`。
- 校正文档分工，减少重复与跨文件职责混乱。

### 11:00 - ATSPI 树快照问题归档
- 归档“导出成功但节点为0/仅顶层节点”问题。
- 增加诊断口径：`tree_attempted/tree_nodes_count/tree_error/raw_mode`。

### 12:00 - 文档职责对齐
- `edit.md`（小时）
- `README.md`（天）
- `ProjectFramework.md`（总框架状态）
- `INSTALL.md`（环境与迁移）

### 13:00 - 模块联调回填
- 前端 `RPATest.vue`、后端 `rpa_compatibility.py`、C++ 绑定能力状态回填。

---

## 2026-02-20

### 10:00 - 点击失败根因定位
- 发现 `click_element` 初期仅依赖 AT-SPI 控件名命中，缺少完整回退路径。

### 11:00 - 三层点击策略落地
- 后端策略链：`AT-SPI -> 坐标拟人化 -> 键盘兜底`。
- 返回字段补充：`strategy/trace/elapsed_ms/total_elapsed_ms`。

### 12:00 - 前端策略轨迹可视化
- `RPATest.vue` 增加策略轨迹面板，便于联调定位。

### 14:00 - AT-SPI 树快照与节点点击验证
- 新增树快照与按边界点击验证接口。
- 联调能力从“结果不可解释”升级为“可观测”。

### 15:00 - 自动激活抓树
- `tree_snapshot` 支持 `auto_activate`，前端新增“一键激活并抓树”按钮。

---

## 2026-02-19

### 23:40 - RPATest 按钮级联调回归
- 修正多处路径与参数传递方式。
- 解决前端 `socket hang up` 与后端崩溃链路问题。

### 23:00 - 高风险接口替换
- 将高风险截图标注路径替换为安全路径（先截图，再 Python 层标注）。

### 22:00 - 历史文档体检
- 识别并修复多文档重复、拼接残段、职责冲突。

---

## 2026-02-18 ~ 2026-02-14（摘要）
- C++ RPA 编译与接口稳定性修复。
- WeChatManager/ATSPI 功能补齐。
- 后端 API 向 C++ 核心迁移。
- 前端联调页持续增强。
- 文档体系首次成型。
