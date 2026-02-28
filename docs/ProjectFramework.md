# WeChat Copilot 项目框架（维护 / 迁移 / 重建指南）

> 本文档目标：让后续维护者在**不依赖历史口口相传**的情况下，能快速理解模块边界、启动方式、关键依赖与迁移重建风险点。
>
> 权威口径：
> - 目录结构以 `tree.md` 为准（定期重扫生成）。
> - 功能现状以根目录 `README.md` 与代码入口为准。
> - `docs/` 下其他文档可能不是最新，本文件优先保证“和当前代码一致”。

## 1. 总体分层

项目当前可按四层理解：

1) **前端（Vue + Vite）**：调试与管理界面（配置、扫描/构建联调、可视化验证等）。

2) **后端（FastAPI）**：统一 REST API、任务编排、兼容路由、数据存储、对接 RPA 与 AI 能力。

3) **RPA 执行层（C++ + Python 封装）**：
- C++ 核心通过 pybind11 导出 `wechat_rpa` Python 模块（窗口管理、AT-SPI、截图、OCR、拟人化等）。
- Python 的 `rpa/` 作为兼容/封装层，在 C++ 模块不可用时提供降级（目前多为模拟/占位）。

4) **AI / LLM 能力层（Python）**：模型路由、场景化请求、工具注册/日志等。

## 2. 仓库目录与职责（以 tree.md 为准）

顶层关键目录：

- `backend/`：FastAPI 服务。
	- 入口：`backend/main.py`
	- 路由：`backend/api/v1/`（包含 rpa、wechat_ops、layout_control、atspi_analysis、llm_core、sop 等）
	- 配置：`backend/core/config.py`（读取 `backend/.env`）
	- 数据：`backend/data/wechat.db`、`backend/data/ui_analysis_profiles.json`
	- 缓存：`backend/cache/ui_cache/`

- `cpp_rpa/`：C++ RPA 核心 + Python 绑定。
	- CMake：`cpp_rpa/CMakeLists.txt`
	- Python 绑定：`cpp_rpa/bindings/python_bindings.cpp`
	- 头文件：`cpp_rpa/include/`
	- 实现：`cpp_rpa/src/`
	- 构建产物（约定）：`cpp_rpa/build/` 下生成 `wechat_rpa*.so`

- `rpa/`：Python 侧的 RPA 兼容/封装层。
	- `rpa/wechat_operator.py`：优先加载 C++ `wechat_rpa`，不可用时 fallback
	- `rpa/controller.py`：对外提供较高层控制函数（激活窗口、获取 UI 元素等）

- `frontend/`：Vite + Vue 前端。
	- `frontend/src/`：页面与组件
	- `frontend/src/api/`：后端 API 调用

- `core/` + `config/`：AI 路由与模型配置（多模型客户端、意图识别、路由策略）。

- `docs/`：框架、规格与SOP类文档（本文档为“当前实现口径”的总览）。

## 3. 关键入口点（维护必看）

### 3.1 后端入口与路由聚合

- 后端服务入口：`backend/main.py`
	- 在 `lifespan` 中初始化数据库表（`backend/db/session.py:create_tables()`）
	- `include_router(...)` 汇总各 API 模块

常见后端模块定位方式：
- 先从 `backend/main.py` 看 include_router 的模块名
- 再到 `backend/api/v1/` 找对应文件

### 3.2 C++ RPA 模块的 Python 导入路径约定

当前 Python 层（如 `rpa/wechat_operator.py`、`backend/api/v1/rpa.py`）依赖 `cpp_rpa/build/` 下的 `wechat_rpa` 模块。

迁移时重点检查：
- 是否已在新机器成功构建出 `cpp_rpa/build/wechat_rpa*.so`
- Python 是否能 `import wechat_rpa`
- 是否存在硬编码路径（见“迁移风险点”）

### 3.3 数据库与落盘位置

- 数据库：SQLite（默认固定在 `backend/data/wechat.db`，避免因启动目录不同读写到不同 DB）
- 结构：由 `SQLModel.metadata.create_all(engine)` 生成（见 `backend/db/models.py` 与 `backend/db/session.py`）

## 4. 启动与构建（最小可用路径）

> 说明：以下命令按仓库已有脚本与入口整理；如果你用的是不同 venv 或不同工作目录，以代码中的实际路径解析逻辑为准。

### 4.1 启动后端

推荐使用脚本：

```bash
./run_backend.sh
```

等价命令（方便排障）：

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

健康检查：
- `GET /health`

### 4.2 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4.3 构建 C++ RPA（可选但多数 RPA 能力依赖它）

```bash
cd cpp_rpa
./build.sh
```

构建完成后，Python 侧应能导入：

```bash
python -c "import wechat_rpa; print('ok')"
```

## 5. 配置约定

### 5.1 后端 .env（backend/.env）

后端配置通过 `backend/core/config.py` 读取，关键字段：

- `database_url`：默认 `sqlite:///../data/wechat.db`
- `llm_api_key` / `llm_base_url` / `llm_model`
- `wechat_version`

模板参考：`backend/.env.example`

### 5.2 多模型路由配置（config/）

多模型（local/doubao/alibaba）路由逻辑在：

- `core/ai_router.py`
- `config/model_config.py`

## 6. 迁移 / 重建检查清单（最容易踩坑的点）

### 6.1 必要依赖

- Python 依赖：以 `backend/requirements.txt` 为准（FastAPI、SQLModel、OCR/图像相关依赖等）
- Node.js 依赖：前端 `frontend/package.json`
- C++ 依赖：OpenCV、pybind11、（可选）Tesseract/Leptonica、（可选）ATSPI（见 `cpp_rpa/CMakeLists.txt` 与 `cpp_rpa/README.md`）

### 6.2 路径与硬编码风险

迁移到新机器/新目录前，建议先全文搜索这些特征：

- 绝对路径（例如包含 `/home/neogh/`）
- 直接拼接 `cpp_rpa/build`

目前已知：
- `backend/api/v1/rpa.py` 中包含多条模块搜索路径，其中一条为硬编码 `/home/neogh/wechat_copilot/cpp_rpa/build`（迁移后需要确保仍能找到构建产物）。

### 6.3 启动脚本与历史遗留

当前仓库根目录的 `run_rpa.sh` 引用了 `rpa/monitor.py`，但当前代码树中并不存在该文件。

含义：
- 监控/常驻 RPA 进程这一“脚本入口”属于历史遗留或待恢复能力；
- 迁移/重建时不要以该脚本作为现状依据，应以 `backend/` API 与 `rpa/` 模块实际存在的入口为准。

（建议做法：如果需要常驻 RPA 进程，优先在后端任务系统或 systemd 方式统一托管；但是否恢复该能力属于功能决策，不在本文档强行定义。）

### 6.4 快速验证顺序（推荐）

1) 后端能启动：`GET /health` 返回 ok
2) 数据库可写：启动时自动建表无报错
3) C++ RPA 可导入：`import wechat_rpa` 成功
4) RPA 状态接口：`GET /api/v1/rpa/status`（或相近路径）能反映模块可用性
5) 前端能连后端：浏览器控制台无跨域/网络错误

## 7. 文档更新规则（面向维护）

- 当以下任一发生变化时更新本文档：
	- 后端入口/路由前缀有较大调整
	- `cpp_rpa` 构建方式、产物位置、导入方式发生改变
	- 数据库存储位置/迁移方式改变
	- 前端与后端交互协议发生结构性变化

- 小范围接口字段、局部 UI、单个任务参数调整不必在此逐条记录（放在对应模块 README 或变更记录里更合适）。
