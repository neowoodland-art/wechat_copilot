#!/usr/bin/env python3
"""
微信RPA Flask API服务器
基于LAVARONG/wechat-automation-api思路
"""

from flask import Flask, request, jsonify
import sys
import os
import json
import time
import threading
import logging
from datetime import datetime

# 直接使用build目录中的模块
build_dir = os.path.join(os.path.dirname(__file__), 'build')
sys.path.insert(0, build_dir)

try:
    import wechat_rpa
    print("✅ 微信RPA模块导入成功")
except ImportError as e:
    print(f"❌ 微信RPA模块导入失败: {e}")
    sys.exit(1)

# 创建Flask应用
app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局管理器实例
manager = None
manager_lock = threading.Lock()

def get_manager():
    """获取管理器实例（线程安全）"""
    global manager
    with manager_lock:
        if manager is None:
            manager = wechat_rpa.WeChatManager()
            manager.initialize()
            logger.info("微信管理器初始化成功")
        return manager

@app.route('/api/status', methods=['GET'])
def api_status():
    """获取API状态"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/wechat/initialize', methods=['POST'])
def api_initialize():
    """初始化微信管理器"""
    try:
        mgr = get_manager()
        result = mgr.initialize()
        return jsonify({
            'success': result,
            'message': '初始化成功' if result else '初始化失败'
        })
    except Exception as e:
        logger.error(f"初始化错误: {e}")
        return jsonify({
            'success': False,
            'message': f'初始化失败: {str(e)}'
        }), 500

@app.route('/api/wechat/activate', methods=['POST'])
def api_activate():
    """激活微信窗口"""
    try:
        mgr = get_manager()
        result = mgr.activate_wechat()
        return jsonify({
            'success': result,
            'message': '激活成功' if result else '激活失败'
        })
    except Exception as e:
        logger.error(f"激活错误: {e}")
        return jsonify({
            'success': False,
            'message': f'激活失败: {str(e)}'
        }), 500

@app.route('/api/wechat/capture', methods=['POST'])
def api_capture():
    """截取微信窗口"""
    try:
        mgr = get_manager()
        
        # 获取参数
        data = request.get_json()
        full_window = data.get('full_window', False)
        
        if full_window:
            screenshot = mgr.capture_full_window()
        else:
            screenshot = mgr.capture_message_area()
        
        # 转换为base64
        import base64
        import io
        import cv2
        
        _, buffer = cv2.imencode('.png', screenshot)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': '截图成功',
            'image': img_base64,
            'width': screenshot.shape[1],
            'height': screenshot.shape[0]
        })
    except Exception as e:
        logger.error(f"截图错误: {e}")
        return jsonify({
            'success': False,
            'message': f'截图失败: {str(e)}'
        }), 500

@app.route('/api/wechat/click', methods=['POST'])
def api_click():
    """点击指定位置"""
    try:
        mgr = get_manager()
        
        # 获取参数
        data = request.get_json()
        x = data.get('x', 0)
        y = data.get('y', 0)
        button = data.get('button', 1)  # 1=左键, 2=中键, 3=右键
        
        # 获取窗口信息
        window = mgr.get_wechat_window()
        
        # 转换为绝对坐标
        abs_x = window.x + x
        abs_y = window.y + y
        
        # 使用 C++ RPA 模块执行点击
        mgr.click_at(abs_x, abs_y, button)
        
        return jsonify({
            'success': True,
            'message': f'点击成功: ({abs_x}, {abs_y})'
        })
    except Exception as e:
        logger.error(f"点击错误: {e}")
        return jsonify({
            'success': False,
            'message': f'点击失败: {str(e)}'
        }), 500

@app.route('/api/wechat/input', methods=['POST'])
def api_input():
    """输入文本"""
    try:
        mgr = get_manager()
        
        # 获取参数
        data = request.get_json()
        text = data.get('text', '')
        
        # 模拟输入
        import subprocess
        cmd = f"xdotool type '{text}'"
        subprocess.run(cmd, shell=True, check=True)
        
        return jsonify({
            'success': True,
            'message': f'输入成功: {text}'
        })
    except Exception as e:
        logger.error(f"输入错误: {e}")
        return jsonify({
            'success': False,
            'message': f'输入失败: {str(e)}'
        }), 500

@app.route('/api/wechat/send_message', methods=['POST'])
def api_send_message():
    """发送消息"""
    try:
        mgr = get_manager()
        
        # 获取参数
        data = request.get_json()
        contact = data.get('contact', '')
        message = data.get('message', '')
        
        # 点击联系人
        # 这里需要实现联系人查找逻辑
        # 暂时使用简单方法
        
        # 点击输入框
        input_result = mgr.click_element('message_input')
        
        # 输入消息
        import subprocess
        cmd = f"xdotool type '{message}'"
        subprocess.run(cmd, shell=True, check=True)
        
        # 点击发送按钮
        send_result = mgr.click_element('send_button')
        
        return jsonify({
            'success': send_result,
            'message': '发送成功' if send_result else '发送失败'
        })
    except Exception as e:
        logger.error(f"发送消息错误: {e}")
        return jsonify({
            'success': False,
            'message': f'发送失败: {str(e)}'
        }), 500

@app.route('/api/wechat/scan_ui', methods=['POST'])
def api_scan_ui():
    """扫描UI元素"""
    try:
        mgr = get_manager()
        
        # 获取参数
        data = request.get_json()
        element_type = data.get('type', 'button')  # button/input/contact
        
        # 扫描UI元素
        elements = mgr.find_ui_elements(element_type)
        
        # 转换为JSON格式
        result = []
        for elem in elements:
            result.append({
                'x': elem.x,
                'y': elem.y,
                'width': elem.width,
                'height': elem.height
            })
        
        return jsonify({
            'success': True,
            'message': f'扫描成功，找到{len(elements)}个{element_type}',
            'elements': result
        })
    except Exception as e:
        logger.error(f"扫描UI错误: {e}")
        return jsonify({
            'success': False,
            'message': f'扫描失败: {str(e)}'
        }), 500

@app.route('/api/wechat/messages', methods=['GET'])
def api_get_messages():
    """获取最新消息"""
    try:
        mgr = get_manager()
        
        # 获取参数
        count = request.args.get('count', 10, type=int)
        
        # 获取消息
        messages = mgr.get_latest_messages(count)
        
        # 转换为JSON格式
        result = []
        for msg in messages:
            result.append({
                'content': msg.content,
                'timestamp': msg.timestamp,
                'sender': msg.sender
            })
        
        return jsonify({
            'success': True,
            'message': f'获取成功，共{len(messages)}条消息',
            'messages': result
        })
    except Exception as e:
        logger.error(f"获取消息错误: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'API端点不存在'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"内部错误: {error}")
    return jsonify({
        'success': False,
        'message': '内部服务器错误'
    }), 500

if __name__ == '__main__':
    print("=== 微信RPA Flask API服务器 ===")
    print("启动服务器，监听端口: 5000")
    print("API文档: http://localhost:5000/api/status")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=False)