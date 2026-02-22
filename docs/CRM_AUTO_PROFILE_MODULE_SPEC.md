# 微信 CRM 全自动聊天沉淀与客户画像模块（可执行标准）

## 1. 模块目标

在现有客户管理系统基础上，新增“聊天沉淀-摘要-画像-标签”闭环能力：

1. 自动抓取微信历史聊天（文字/图片/语音/文件）并统一入库。
2. 以“单客户”维度维护可追溯聊天资产。
3. 每日或每 3 天自动生成聊天精简摘要。
4. 基于摘要生成客户画像并自动回填标签。
5. 为后续沟通、SOP、运营动作提供标准化输入。

---

## 2. 系统边界与依赖

### 2.1 复用现有能力

- 微信自动化采集：RPA/ATSPI 相关接口。
- 大模型统一入口：`POST /api/v1/llm/core`。
- 客户基础信息：`User`（或后续 Customer 主表）。

### 2.2 新增能力范围

- 聊天全量采集与归档。
- 多模态消息转文字（OCR/ASR/文件解析）。
- 定时摘要、画像与标签任务。
- 数据导入/导出与人工修正流程。

---

## 3. 数据模型（DDL 草案）

> 说明：若你继续沿用当前 SQLite + SQLModel，可先按字段落表，再补迁移脚本；若切 MySQL，字段保持一致。

### 3.1 `wechat_chat_history`

```sql
CREATE TABLE IF NOT EXISTS wechat_chat_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  session_id VARCHAR(128) DEFAULT '',
  msg_id VARCHAR(128) NOT NULL,
  msg_type VARCHAR(32) NOT NULL,         -- text/image/audio/file/system
  sender VARCHAR(16) NOT NULL,           -- me/other/system
  content_raw TEXT,                      -- 原始文本/描述
  content_text TEXT,                     -- 转写后文本（OCR/ASR/解析）
  content_json JSON NULL,                -- 扩展结构（检测框、ASR置信度、文件元数据）
  file_path VARCHAR(1024) DEFAULT '',
  file_hash VARCHAR(128) DEFAULT '',
  ocr_status VARCHAR(16) DEFAULT 'none', -- none/pending/success/failed
  asr_status VARCHAR(16) DEFAULT 'none',
  parse_status VARCHAR(16) DEFAULT 'none',
  send_time DATETIME NOT NULL,
  imported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_customer_msg (customer_id, msg_id),
  KEY idx_customer_time (customer_id, send_time),
  KEY idx_msg_type (msg_type)
);
```

### 3.2 `chat_summary`

```sql
CREATE TABLE IF NOT EXISTS chat_summary (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  summary_scope VARCHAR(32) NOT NULL,      -- daily/3day/weekly/manual
  summary_days INT NOT NULL DEFAULT 3,
  range_start DATETIME NOT NULL,
  range_end DATETIME NOT NULL,
  summary_content TEXT NOT NULL,
  summary_json JSON NULL,
  model_used VARCHAR(64) DEFAULT '',
  model_version VARCHAR(64) DEFAULT '',
  token_in INT NOT NULL DEFAULT 0,
  token_out INT NOT NULL DEFAULT 0,
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_customer_generated (customer_id, generated_at),
  KEY idx_scope (summary_scope)
);
```

### 3.3 `customer_portrait`

```sql
CREATE TABLE IF NOT EXISTS customer_portrait (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  portrait_version VARCHAR(32) DEFAULT 'v1',
  portrait_content TEXT NOT NULL,
  portrait_json JSON NOT NULL,
  personality VARCHAR(255) DEFAULT '',
  preference VARCHAR(255) DEFAULT '',
  core_needs VARCHAR(255) DEFAULT '',
  purchase_intention VARCHAR(32) DEFAULT '', -- high/medium/low
  budget_level VARCHAR(32) DEFAULT '',
  taboo TEXT,
  best_contact_time VARCHAR(64) DEFAULT '',
  confidence DECIMAL(5,4) DEFAULT 0.0,
  source_summary_ids VARCHAR(1024) DEFAULT '',
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_customer_generated (customer_id, generated_at)
);
```

### 3.4 `customer_tag_snapshot`

```sql
CREATE TABLE IF NOT EXISTS customer_tag_snapshot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  tag_name VARCHAR(128) NOT NULL,
  tag_type VARCHAR(64) NOT NULL,
  tag_score DECIMAL(5,4) DEFAULT 0.0,
  source VARCHAR(64) DEFAULT 'llm',          -- llm/manual/rule
  source_ref VARCHAR(128) DEFAULT '',        -- portrait_id/summary_id
  generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_customer_tag (customer_id, tag_name),
  KEY idx_tag_type (tag_type)
);
```

---

## 4. 统一 API 合同（后端）

## 4.1 数据采集

- `POST /api/v1/crm/chat/import/wechat`
  - 功能：按客户或批量抓取微信历史消息并入库。
  - 入参：`customer_id | wechat_id | range_start/range_end | include_media`
  - 出参：`imported_count/skipped_count/failed_count`

- `POST /api/v1/crm/chat/import/convert`
  - 功能：将待处理图片/语音/文件转为文本并回填。
  - 入参：`customer_id | batch_size | msg_types`
  - 出参：`ocr_success/asr_success/parse_success`

## 4.2 历史查询与导入导出

- `GET /api/v1/crm/chat/history`
  - 过滤：`customer_id,msg_type,sender,start,end,page,page_size,keyword`

- `GET /api/v1/crm/chat/export`
  - 格式：`json/csv`
  - 维度：`customer_id + 时间范围`

- `POST /api/v1/crm/chat/import/file`
  - 功能：导入历史聊天文件（迁移/回灌场景）。

## 4.3 摘要、画像、标签

- `POST /api/v1/crm/summary/generate`
  - 功能：触发单客户摘要（daily/3day/manual）。

- `POST /api/v1/crm/portrait/generate`
  - 功能：基于摘要生成画像。

- `POST /api/v1/crm/tags/generate`
  - 功能：基于画像生成标签并回填客户标签体系。

- `GET /api/v1/crm/profile/overview`
  - 功能：返回单客户的“原始记录 + 摘要 + 画像 + 标签”视图。

## 4.4 定时任务配置

- `GET /api/v1/crm/schedule/config`
- `POST /api/v1/crm/schedule/config`
- `POST /api/v1/crm/schedule/run-now`

---

## 5. 与 `llm/core` 对接规范（强制）

## 5.1 摘要场景

- `scene_type`: `sop_generation`
- `input.structured_data` 至少包含：
  - `customer_info`
  - `chat_history`
  - `date_info`
  - `summary_scope`

## 5.2 画像与标签场景

- 推荐 `scene_type`: `system_evolution` 或新增 `customer_portrait`（若你后续扩展 scene）
- 当前项目可先复用 `sop_generation` 并在 `config.ext.task_type` 传：
  - `portrait_generate`
  - `tag_generate`

## 5.3 Token 优化规则

调用 `llm/core` 时统一附带：

```json
{
  "config": {
    "response_format": "json",
    "ext": {
      "max_history": 10,
      "max_images": 1,
      "max_text_chars": 2000
    }
  }
}
```

---

## 6. LLM 输出 JSON 标准（给模型的硬约束）

## 6.1 聊天摘要输出

```json
{
  "customer_id": "CUST001",
  "summary_time": "2026-02-22",
  "summary_days": 3,
  "key_content": ["..."],
  "important_event": ["..."],
  "requirement": ["..."],
  "question": ["..."],
  "commitment": ["..."],
  "risk_alert": ["..."]
}
```

## 6.2 客户画像输出

```json
{
  "customer_id": "CUST001",
  "portrait": {
    "personality": "理性/直接",
    "preference": "重视性价比",
    "core_needs": "稳定、省心",
    "purchase_intention": "high",
    "budget_level": "medium",
    "taboo": ["不喜欢被催促"],
    "best_contact_time": "工作日下午",
    "communication_style": "先需求后推荐",
    "confidence": 0.86
  }
}
```

## 6.3 标签输出

```json
{
  "customer_id": "CUST001",
  "tags": [
    {"name": "高意向", "type": "intent", "score": 0.92},
    {"name": "理性型", "type": "personality", "score": 0.81},
    {"name": "关注性价比", "type": "preference", "score": 0.88}
  ]
}
```

---

## 7. 前端交互规划（页面级）

建议在现有客户管理页基础上新增 4 个子视图（可做 tabs）：

1. **聊天记录**：原始消息流 + 媒体转写结果 + 时间筛选。
2. **摘要记录**：daily/3day 摘要列表，支持人工修订。
3. **客户画像**：结构化画像展示，支持“采纳/覆盖/回滚”。
4. **标签管理**：标签来源、分值、更新时间，支持手工增删改。

页面动作：

- 手动触发：导入聊天、生成摘要、生成画像、刷新标签。
- 数据导出：聊天/摘要/画像导出 JSON/CSV。
- 任务配置：设置 1/3/7 天频率与启停状态。

---

## 8. 自动化任务策略

默认计划：

1. 每天 00:30：导入前一日聊天并做媒体转写。
2. 每 3 天 01:00：生成 3 天摘要。
3. 每 7 天 02:00：生成画像并刷新标签。

失败处理：

- 同客户重试最多 2 次。
- 写入任务日志（成功/失败/耗时/错误）。
- 失败不阻断其他客户任务。

---

## 9. 导入导出规范

## 9.1 导出包结构

```json
{
  "customer": {},
  "chat_history": [],
  "summaries": [],
  "portraits": [],
  "tags": []
}
```

## 9.2 幂等导入规则

- `chat_history`: `(customer_id, msg_id)` 去重。
- `summary`: `(customer_id, range_start, range_end, summary_scope)` 去重。
- `portrait`: 保留历史版本，最新版本置顶。

---

## 10. 安全与合规

- 客户敏感字段支持脱敏导出（手机号、证件号等）。
- 文件路径不直接暴露磁盘绝对路径，走受控下载接口。
- LLM 入参默认裁剪，避免泄露无关历史。

---

## 11. 交付验收清单

1. 可完成单客户全量历史导入（含图片/OCR文本）。
2. 可生成 daily/3day 摘要并可回溯。
3. 可生成客户画像并转标签回填。
4. 前端可查看全链路：历史→摘要→画像→标签。
5. 支持 JSON/CSV 导出与 JSON 导入。
6. 定时任务可配置、可手工触发、可查看日志。

---

## 12. 可直接喂给智能体的开发指令（模板）

```text
请基于当前项目（FastAPI + SQLModel + Vue + 现有 /api/v1/llm/core）实现 CRM 全自动聊天沉淀模块：

1) 新增表：wechat_chat_history、chat_summary、customer_portrait、customer_tag_snapshot；
2) 新增接口：
   - /api/v1/crm/chat/import/wechat
   - /api/v1/crm/chat/import/convert
   - /api/v1/crm/chat/history
   - /api/v1/crm/chat/export
   - /api/v1/crm/summary/generate
   - /api/v1/crm/portrait/generate
   - /api/v1/crm/tags/generate
   - /api/v1/crm/profile/overview
   - /api/v1/crm/schedule/config
   - /api/v1/crm/schedule/run-now
3) 所有摘要/画像/标签生成必须复用 /api/v1/llm/core，并严格输出 JSON；
4) 采用 token 节流参数：max_history/max_images/max_text_chars；
5) 前端在 Customers 页面新增“聊天记录/摘要/画像/标签”四个子视图；
6) 支持导入导出与人工修正；
7) 提供最小可运行版本与 OpenAPI 描述。
```
