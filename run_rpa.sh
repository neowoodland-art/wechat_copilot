#!/bin/bash
cd /home/neogh/wechat_copilot
source .venv/bin/activate

echo "启动微信 RPA 监控..."
python rpa/monitor.py --mode continuous
