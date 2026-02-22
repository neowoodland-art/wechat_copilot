# WeChat Copilot

Linux 微wx自动化项目，当前架构为：**C++ RPA 核心 + Python/FastAPI 服务层 + Vue 前端测试与管理界面**。

## 今日与近期总结（按天）

### 2026-02-22
- 完成鼠标扫描异步任务化：支持开始/状态/取消，前端可中断并显示进度。
- 完成扫描后构建确认图闭环：构建成功后自动展示标注预览截图。
- 修复“区域范围未生效”问题：扫描/构建统一按模板化配置名执行（`_chat/_contacts`）。
- 新增区域级调试摘要：每区扫描点数与候选数量可视化，用于定位差分识别缺失问题。
- 完成项目文档体系同步更新（tree/edit/README/INSTALL/Framework/C++文档）。

### 2026-02-21
- 完成全项目目录重扫并更新 `tree.md`。
- 统一 ATSPI 辅助树问题排障口径与诊断字段。
- 整理文档职责边界（小时记录/天总结/框架总览/安装迁移）。

### 2026-02-20
- 修复点击链路可观测性不足，落地三层点击策略（AT-SPI → 坐标拟人化 → 键盘兜底）。
- 前端增加策略轨迹可视化，支持快速定位失败层。
- 增加 AT-SPI 树快照与节点边界点击验证能力。

### 2026-02-19
- 解决前后端联调过程中的 `socket hang up` 与服务崩溃问题。
- 高风险截图标注链路改为安全路径，后端稳定性明显提升。

## 目录说明
- `backend/`：FastAPI 后端（API、业务编排、数据存储）。
- `frontend/`：Vite + Vue 前端调试与管理页面。
- `cpp_rpa/`：C++ 微wx自动化核心模块（含 pybind11 绑定）。
- `rpa/`：Python 侧兼容/封装层。
- `docs/`：规格与SOP文档。

## 当前重点能力
- 微wx窗口锁定与布局控制。
- 模板化区域标注（聊天/联系人）。
- 鼠标扫描（可中断、可观测进度、区域调试）。
- 标注构建后截图确认。
- ATSPI 树快照与节点点击验证。

## 快速启动
```bash
# 后端
source /home/neogh/wechat_copilot/.venv/bin/activate
cd /home/neogh/wechat_copilot/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
cd /home/neogh/wechat_copilot/frontend
npm run dev
```

更多环境、迁移、启停、配置细节见 `INSTALL.md`。
