#!/bin/bash
# 激活微信窗口并启动监控
xdotool search --name "微信" windowactivate || echo "⚠️ 未找到微信窗口"
python -m rpa.monitor
