# 项目目录结构（最近扫描：2026-02-22 12:00）

```text
wechat_copilot/
├── .vscode/
│   └── settings.json
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── sop/
│   │       ├── __init__.py
│   │       ├── layout_control.py
│   │       ├── message_ops.py
│   │       ├── messages.py
│   │       ├── rpa.py
│   │       ├── rpa_compatibility.py
│   │       ├── rpa_control.py
│   │       ├── sop.py
│   │       ├── sop_management.py
│   │       ├── ui_analysis.py
│   │       ├── users.py
│   │       └── wechat_ops.py
│   ├── cache/
│   │   └── ui_cache/
│   ├── core/
│   │   ├── ai_client.py
│   │   └── config.py
│   ├── data/
│   │   ├── ui_analysis_profiles.json
│   │   └── wechat.db
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   ├── static/
│   ├── tasks/
│   ├── .env.example
│   ├── backend_debug.log
│   ├── main.py
│   └── requirements.txt
├── config/
│   ├── __init__.py
│   └── model_config.py
├── core/
│   ├── __init__.py
│   ├── ai_client.py
│   ├── ai_router.py
│   ├── cache_manager.py
│   └── intent_detector.py
├── cpp_rpa/
│   ├── .vscode/
│   │   └── launch.json
│   ├── bindings/
│   │   └── python_bindings.cpp
│   ├── examples/
│   │   ├── basic_usage.py
│   │   └── basic_usage_with_timeout.py
│   ├── include/
│   │   ├── atspi_engine.h
│   │   ├── atspi_engine.h.backup
│   │   ├── atspi_engine.h.backup_fix
│   │   ├── common.h
│   │   ├── common.h.backup_exception
│   │   ├── common.h.backup_precise
│   │   ├── common.h.backup_with_errors
│   │   ├── humanization_engine.h
│   │   ├── image_processor.h
│   │   ├── ocr_engine.h
│   │   ├── wechat_manager.h
│   │   └── window_manager.h
│   ├── src/
│   │   ├── atspi_engine.cpp
│   │   ├── humanization_engine.cpp
│   │   ├── humanization_engine_clean.cpp
│   │   ├── image_processor.cpp
│   │   ├── ocr_engine.cpp
│   │   ├── wechat_manager.cpp
│   │   └── window_manager.cpp
│   ├── analyze_wechat_windows.py
│   ├── build.sh
│   ├── build_and_test.sh
│   ├── build_basic.sh
│   ├── build_corrected.sh
│   ├── build_fixed.sh
│   ├── build_simple.sh
│   ├── CMakeLists.txt
│   ├── CMakeLists.txt.failed
│   ├── compile_and_run.sh
│   ├── complete_fix.sh
│   ├── debug.gdb
│   ├── fix_atspi_file.sh
│   ├── IMPLEMENTATION_PLAN.md
│   ├── install_atspi.sh
│   ├── install_deps.sh
│   ├── install_ydotool.sh
│   ├── interface_elements.json
│   ├── mouse_scan_test.py
│   ├── os
│   ├── README.md
│   ├── rebuild.sh
│   ├── reference.txt
│   ├── simple_test.py
│   ├── subprocess
│   ├── sys
│   ├── test_atspi.py
│   ├── test_cpp_atspi_only.py
│   ├── test_humanization.py
│   ├── test_simple.py
│   ├── test_wechat_window.py
│   ├── test_wechatUI_0209_2023.py
│   ├── test_xdotool_direct.py
│   ├── wechat_analyzer.py
│   ├── wechat_api_server.py
│   ├── wechat_ui_enhanced.py
│   ├── wechat_ui_interact.py
│   └── wechat_windows.json
├── data/
├── docs/
│   ├── sop_api_documentation.md
│   ├── suo.md
│   └── wechat_ui_fusion_spec.md
├── frontend/
│   ├── dist/
│   │   ├── assets/
│   │   │   ├── index-BySbm9qU.js
│   │   │   └── index-GZQd8q_d.css
│   │   └── index.html
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   │   └── index.js
│   │   ├── assets/
│   │   ├── components/
│   │   │   └── SOPVisualEditor.vue
│   │   ├── router/
│   │   ├── store/
│   │   ├── views/
│   │   │   ├── AIAssistant.vue
│   │   │   ├── CustomerRetargeting.vue
│   │   │   ├── Customers.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── RPATest.vue
│   │   │   ├── Settings.vue
│   │   │   ├── SOPEditor.vue
│   │   │   ├── SOPManagement.vue
│   │   │   ├── SOPTemplates.vue
│   │   │   ├── UserDetail.vue
│   │   │   ├── UserList.vue
│   │   │   └── WeChatAutomation.vue
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   └── vite.config.js
├── rpa/
│   ├── __init__.py
│   ├── capture.py
│   ├── controller.py
│   ├── test_controller.py
│   ├── ui_analyzer.py
│   ├── wechat_activator.py
│   └── wechat_operator.py
├── # C++ RPA模块API参考文档.md
├── .env.example
├── actweixin.sh
├── backend.log
├── C++_RPA_Framework_Design.md
├── edit.md
├── fix_cpp_rpa_compilation.sh
├── fix_image_processor.sh
├── fix_method_calls.sh
├── fix_rpa_exception.sh
├── fix_wechat_manager_simple.sh
├── fixed_common.h
├── information.txt
├── INSTALL.md
├── jjjccc.py
├── plan_objectives.md
├── precise_fix_common_h.sh
├── ProjectFramework.md
├── README.md
├── run_backend.sh
├── run_rpa.sh
├── simple_capture_impl.sh
├── test_annotated_ui.py
├── test_fixed_rpa.py
├── test_module.py
├── test_ui_elements.py
├── traceback
├── tree.md
└── 图片_2026-02-13_174715_201.png

34 directories, 153 files
```

> 扫描口径：本次为全项目重扫，未展开 `.git/`、`.venv/`、`node_modules/`、`__pycache__/`、`cpp_rpa/build/`。
> 说明：`frontend/dist/` 作为当前已有构建产物已保留展示。
