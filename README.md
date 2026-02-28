# WeChat Copilot（项目功能及模块介绍）

Linux 微信自动化项目，当前架构为 **C++ RPA 核心 + Python/FastAPI 服务层 + Vue 前端管理界面**。

## 能力范围（当前可用）

- 微信窗口检测与激活（基于 C++ RPA 核心）。
- AT-SPI 辅助树分析与控件交互能力（可用时优先走 AT-SPI）。
- 截图与 OCR（取决于 C++ 依赖是否齐全）。
- 聊天/联系人区域模板化扫描与标注构建。
- 扫描任务可观测与可中断（前端进度与结果回传）。
- 标注构建后预览截图确认。

## 目录说明

- `backend/`：FastAPI 后端（API、业务编排、数据存储）。
- `frontend/`：Vite + Vue 前端调试与管理页面。
- `cpp_rpa/`：C++ 微信自动化核心模块（含 pybind11 绑定）。
- `rpa/`：Python 侧兼容/封装层。
- `docs/`：规格与SOP文档。

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

原子控件从筛选到入库再到操作打包调用的完整流程见 `docs/原子控件生成与操作打包衔接说明.md`。

欢迎有兴趣的交流与反馈，加入我们的 QQ 群：121374940。