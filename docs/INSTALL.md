# WeChat Copilot 安装、运行与迁移指南
说明依赖和外部工具还有硬件系统环境等各种要求。还有测试工作说明，脚本运行说明。

## 1. 环境基线

### 1.1 硬件建议
- CPU：4核起步，推荐 8 核以上。
- 内存：8GB 起步，推荐 16GB 以上。
- 磁盘：建议至少 10GB 可用空间。

### 1.2 软件版本
- Linux（优先 X11 会话）。
- Python：3.11（项目当前标准）。
- Node.js：16+。
- npm：8+。
- CMake：3.14+。
- GCC/Clang：支持 C++17。

### 1.3 包管理与虚拟环境
- Python 虚拟环境：`venv`（固定路径 `.venv/`）。
- Python 包管理：`pip`（依赖来源 `backend/requirements.txt`）。
- 前端包管理：`npm`（依赖来源 `frontend/package.json`）。
- C++ 构建：`cmake + make`（脚本化入口在 `cpp_rpa/*.sh`）。

## 2. 依赖安装

### 2.1 系统依赖（Ubuntu/Debian）
```bash
sudo apt update
sudo apt install -y build-essential cmake \
  libopencv-dev libleptonica-dev libtesseract-dev tesseract-ocr tesseract-ocr-chi-sim \
  python3-dev python3-pip xdotool wmctrl maim libatspi2.0-dev
```

### 2.2 Python 环境
```bash
cd /home/neogh/wechat_copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2.3 前端依赖
```bash
cd /home/neogh/wechat_copilot/frontend
npm install
```

## 3. C++ RPA 模块构建

### 3.1 构建
```bash
cd /home/neogh/wechat_copilot/cpp_rpa
./build.sh
# 编译异常时可尝试
./build_fixed.sh
```

### 3.2 导入验证
```bash
cd /home/neogh/wechat_copilot
source .venv/bin/activate
python -c "import sys; sys.path.insert(0, 'cpp_rpa/build'); import wechat_rpa; print('ok')"
```

## 4. 项目运行与停止

### 4.1 启动后端
```bash
source /home/neogh/wechat_copilot/.venv/bin/activate
cd /home/neogh/wechat_copilot/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4.2 启动前端
```bash
cd /home/neogh/wechat_copilot/frontend
npm run dev
```

### 4.3 脚本方式
```bash
cd /home/neogh/wechat_copilot
./run_backend.sh
./run_rpa.sh
```

### 4.4 停止命令
```bash
pkill -f "uvicorn main:app"
pkill -f "vite"
pkill -f "wechat_api_server.py"
```

## 5. 配置文件位置与注意事项

### 5.1 关键配置
- 后端环境变量：`backend/.env`（参考 `backend/.env.example`）。
- 模型配置：`config/model_config.py`。
- 前端代理：`frontend/vite.config.js`。
- UI 扫描配置存储：`backend/data/ui_analysis_profiles.json`。
- 业务数据库：`backend/data/wechat.db`。

### 5.2 新使用者必须修改/确认
1. API 密钥与模型配置。
2. 本机窗口控制权限（`xdotool/wmctrl` 可用）。
3. AT-SPI 环境可用性与微信窗口焦点。
4. 锁窗预设是否符合当前桌面布局。
5. 扫描模板配置名与模板类型是否一致（`xxx_chat`/`xxx_contacts`）。

## 6. ATSPI 与桌面环境检查

### 6.1 服务进程检查
```bash
ps -ef | grep -E "at-spi|registryd" | grep -v grep
```

### 6.2 X11 权限（需要时）
```bash
xhost +si:localuser:$(whoami)
```

## 7. 扫描与构建相关 API（运行期重点）

### 7.1 扫描任务（异步）
- `POST /api/v1/rpa/wechat/ui_profile/full_scan_async/start`
- `GET /api/v1/rpa/wechat/ui_profile/full_scan_async/status?task_id=...`
- `POST /api/v1/rpa/wechat/ui_profile/full_scan_async/cancel`

### 7.2 配置构建与确认
- `POST /api/v1/rpa/wechat/ui_profile/build`
- `GET /api/v1/rpa/wechat/ui_profile/annotated_preview?profile_name=...`

### 7.3 常见联调顺序
1. 固定窗口（fix_window）。
2. 启动异步扫描并观察进度。
3. 必要时中断扫描。
4. 调整标注并构建配置。
5. 查看构建后标注确认图。

## 8. 迁移清单（必须保留）
- `backend/.env`。
- `backend/data/wechat.db`。
- `backend/data/ui_analysis_profiles.json`。
- `cpp_rpa/`（含 `include/src/bindings`）。
- 文档：`README.md`、`edit.md`、`ProjectFramework.md`、`INSTALL.md`、C++两份文档。

## 9. 迁移后验收步骤
1. 重建 `.venv` 并安装 Python 依赖。
2. 重新构建 `cpp_rpa` 并验证 `wechat_rpa` 导入。
3. 启动后端与前端。
4. 验证窗口锁定与扫描任务三接口。
5. 验证标注构建与确认图生成。

## 10. 环境调整记录

### 2026-02-22（按天）
- 运行期新增扫描任务异步接口，支持进度轮询与中断。
- 扫描流程统一使用模板化 profile 命名，区域范围命中稳定性提升。
- 新增构建后标注确认图接口，形成“扫描-构建-确认”闭环。

### 2026-02-21（按天）
- 完成项目全目录重扫，文档口径统一。
- 锁窗与 ATSPI 排障口径同步到文档体系。

## 11. 学习与操作指南
- 控件生成与微信操作（含流程图）：`docs/控件生成与微信操作使用说明.md`
