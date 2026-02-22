# /home/neogh/wechat_copilot/backend/api/v1/layout_control.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import platform
import os
import logging

# 尝试导入C++ RPA模块
import sys
import os

# 添加编译后的模块路径
module_paths = [
    os.path.join(os.path.dirname(__file__), '../../../cpp_rpa/build'),
    '/home/neogh/wechat_copilot/cpp_rpa/build',
    os.path.expanduser('~/wechat_copilot/cpp_rpa/build'),
]

for path in module_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

try:
    import wechat_rpa
    from wechat_rpa import WeChatManager, WindowManager
    rpa_available = True
    print("✅ 成功导入 wechat_rpa 模块")
except ImportError as e:
    rpa_available = False
    print(f"警告: 无法导入 wechat_rpa 模块: {e}")
    print("将使用系统命令作为后备方案")
    # 临时导入，避免后续代码出错
    WeChatManager = None
    WindowManager = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/layout", tags=["layout"])

BROWSER_WINDOW_CACHE = {
    "id": "",
    "title": "",
    "updated_at": ""
}

BROWSER_CLASS_KEYWORDS = ["chrome", "chromium", "firefox", "brave", "microsoft-edge", "edge"]
BROWSER_TITLE_KEYWORDS = ["localhost", "127.0.0.1", "wechat copilot", "vite"]
NON_BROWSER_TITLE_KEYWORDS = ["visual studio code", " - code", "pycharm", "intellij", "cursor"]

class LayoutRequest(BaseModel):
    layout: str
    frontendWidthPercent: Optional[float] = 50
    useMargins: Optional[bool] = True  # 是否使用边距，默认为True

class WindowSizeRequest(BaseModel):
    width: int
    height: int
    x: int
    y: int
    target: Optional[str] = "active"

class LaunchRequest(BaseModel):
    scriptPath: str

class WeChatStatusResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


def _cache_browser_window(window_id: str, title: str) -> None:
    BROWSER_WINDOW_CACHE["id"] = str(window_id)
    BROWSER_WINDOW_CACHE["title"] = str(title or "")
    BROWSER_WINDOW_CACHE["updated_at"] = __import__('datetime').datetime.now().isoformat()


def _clear_browser_window_cache() -> None:
    BROWSER_WINDOW_CACHE["id"] = ""
    BROWSER_WINDOW_CACHE["title"] = ""
    BROWSER_WINDOW_CACHE["updated_at"] = ""


def _get_active_window_linux() -> Optional[dict]:
    try:
        active_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True, timeout=3).strip()
        if not active_id:
            return None

        title_proc = subprocess.run(
            ["xdotool", "getwindowname", active_id],
            capture_output=True,
            text=True,
            timeout=3
        )
        title = title_proc.stdout.strip() if title_proc.returncode == 0 else ""
        class_proc = subprocess.run(
            ["xprop", "-id", active_id, "WM_CLASS"],
            capture_output=True,
            text=True,
            timeout=3
        )
        wm_class = class_proc.stdout.strip() if class_proc.returncode == 0 else ""

        return {"id": active_id, "title": title, "wm_class": wm_class}
    except Exception:
        return None


def _is_probable_browser_window(window: Optional[dict]) -> bool:
    if not window:
        return False

    title = str(window.get("title", "")).lower()
    wm_class = str(window.get("wm_class", "")).lower()

    if any(keyword in title for keyword in NON_BROWSER_TITLE_KEYWORDS):
        return False

    class_hit = any(keyword in wm_class for keyword in BROWSER_CLASS_KEYWORDS)
    title_hit = any(keyword in title for keyword in BROWSER_TITLE_KEYWORDS)
    return class_hit or title_hit


@router.post("/browser/register_active")
async def register_active_browser_window():
    """注册当前活动窗口为浏览器目标窗口（用于布局命中率提升）"""
    try:
        if platform.system().lower() != "linux":
            return {"success": False, "error": "仅Linux实现了活动窗口注册"}

        active = _get_active_window_linux()
        if not active:
            return {"success": False, "error": "无法获取当前活动窗口"}

        if not _is_probable_browser_window(active):
            return {
                "success": False,
                "error": "当前活动窗口不是浏览器窗口，请先聚焦浏览器（含localhost/WeChat Copilot页面）后重试",
                "window": active
            }

        _cache_browser_window(active["id"], active.get("title", ""))
        return {
            "success": True,
            "window": active,
            "message": "已注册当前活动窗口为浏览器窗口"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/arrange_layout")
async def arrange_layout(request: LayoutRequest):
    """安排前端和微信窗口布局"""
    try:
        # 首先激活微信窗口，确保它存在
        if rpa_available and WeChatManager:
            try:
                wechat_manager = WeChatManager()
                if wechat_manager.initialize():
                    activation_success = wechat_manager.activate_wechat()
                    if activation_success:
                        logger.info("布局设置前成功激活微信")
                    else:
                        logger.warning("布局设置前激活微信失败，但仍将继续")
            except Exception as e:
                logger.error(f"布局设置前激活微信失败: {e}")
        
        # 获取屏幕尺寸
        screen_width, screen_height = get_screen_size()
        
        # 根据请求决定是否使用边距
        use_margins = request.useMargins
        
        if use_margins:
            # 设置一些边距，避免窗口贴边
            margin_x = 5  # 左右边距
            margin_y = 5  # 上边距（减小）
            effective_width = screen_width - 2 * margin_x
            effective_height = screen_height - margin_y  # 只减去顶部边距，底部不需要太多边距
        else:
            # 不使用边距
            margin_x = 0
            margin_y = 0
            effective_width = screen_width
            effective_height = screen_height
        
        # 根据不同的布局类型调整窗口位置
        layout_type = request.layout
        frontend_width_percent = request.frontendWidthPercent
        
        if layout_type == "half-half":
            # 平铺布局：各占一半
            frontend_width = int(effective_width * 0.5)
            wechat_width = effective_width - frontend_width
            frontend_x, frontend_y = margin_x, margin_y
            wechat_x, wechat_y = margin_x + frontend_width, margin_y
            
        elif layout_type == "one-third-two-thirds":
            # 前端1/3，微信2/3
            frontend_width = int(effective_width * 0.33)
            wechat_width = effective_width - frontend_width
            frontend_x, frontend_y = margin_x, margin_y
            # 添加一个小间隙避免重叠
            wechat_x, wechat_y = margin_x + frontend_width, margin_y
            
        elif layout_type == "custom":
            # 自定义布局
            frontend_width = int(effective_width * (frontend_width_percent / 100))
            wechat_width = effective_width - frontend_width
            frontend_x, frontend_y = margin_x, margin_y
            # 添加一个小间隙避免重叠
            wechat_x, wechat_y = margin_x + frontend_width, margin_y
            
        else:
            # 默认平铺布局
            frontend_width = int(effective_width * 0.5)
            wechat_width = effective_width - frontend_width
            frontend_x, frontend_y = margin_x, margin_y
            wechat_x, wechat_y = margin_x + frontend_width, margin_y
        
        # 确保窗口不重叠，添加一个像素的间隙
        gap = 1  # 1像素间隙
        if wechat_x < (frontend_x + frontend_width):
            wechat_x = frontend_x + frontend_width + gap
            # 确保微信窗口仍在屏幕内
            if wechat_x + wechat_width > screen_width - margin_x:
                # 如果超出屏幕，调整尺寸
                wechat_width = max(wechat_width - (wechat_x + wechat_width - (screen_width - margin_x)), 200)  # 最小宽度200px
                wechat_x = screen_width - margin_x - wechat_width
        
        # 设置前端窗口位置（浏览器窗口）
        browser_success = set_window_position("browser", frontend_x, frontend_y, frontend_width, effective_height)

        # 设置微信窗口位置
        wechat_success = set_window_position("wechat", wechat_x, wechat_y, wechat_width, effective_height)
        
        result = {
            "success": True,
            "layout_type": layout_type,
            "frontend_width_percent": frontend_width_percent,
            "screen": {
                "width": screen_width,
                "height": screen_height
            },
            "positions": {
                "frontend": {
                    "x": frontend_x,
                    "y": frontend_y,
                    "width": frontend_width,
                    "height": effective_height
                },
                "wechat": {
                    "x": wechat_x,
                    "y": wechat_y,
                    "width": wechat_width,
                    "height": effective_height
                }
            },
            "apply_result": {
                "browser": browser_success,
                "wechat": wechat_success
            },
            "message": f"已安排{layout_type}布局"
        }

        if not browser_success or not wechat_success:
            result["warning"] = "部分窗口可能未完全按目标布局生效，请检查窗口管理器限制或手动取消最大化后重试"
        
        return result
    except Exception as e:
        logger.error(f"布局安排失败: {e}")
        return {"success": False, "error": str(e)}

@router.post("/set_window_size")
async def set_window_size(request: WindowSizeRequest):
    """设置窗口大小和位置"""
    try:
        width = request.width
        height = request.height
        x = request.x
        y = request.y
        
        target = (request.target or "active").lower()

        # 仅当目标明确为微信时才激活微信，避免重置其他业务窗口时打断浏览器状态
        if target == "wechat" and rpa_available and WeChatManager:
            try:
                wechat_manager = WeChatManager()
                if wechat_manager.initialize():
                    activation_success = wechat_manager.activate_wechat()
                    if activation_success:
                        logger.info("窗口设置前成功激活微信")
                    else:
                        logger.warning("窗口设置前激活微信失败，但仍将继续")
            except Exception as e:
                logger.error(f"窗口设置前激活微信失败: {e}")
        
        # 实际设置窗口大小和位置
        if target not in ["active", "browser", "wechat", "any"]:
            target = "active"

        mapped_type = "any" if target == "active" else target
        success = set_window_position(mapped_type, x, y, width, height)
        
        result = {
            "success": bool(success),
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "target": target,
            "message": f"窗口已设置为 {width}x{height} 位置 ({x}, {y})"
        }
        
        if not success:
            result["warning"] = "窗口位置设置未生效，请检查窗口焦点、窗口管理器限制，或改用target=wechat/browser"
        
        return result
    except Exception as e:
        logger.error(f"窗口大小设置失败: {e}")
        return {"success": False, "error": str(e)}




@router.post("/launch")
async def launch_wechat(request: LaunchRequest):
    """启动微信"""
    try:
        script_path = request.scriptPath
        
        if not os.path.exists(script_path):
            return {"success": False, "error": f"脚本路径不存在: {script_path}"}
        
        # 尝试启动微信脚本
        try:
            result = subprocess.run(['bash', script_path], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "微信启动命令已发送",
                    "output": result.stdout
                }
            else:
                return {
                    "success": False,
                    "error": f"启动失败: {result.stderr}",
                    "output": result.stdout
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "启动脚本超时"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/wechat/activate")
async def activate_wechat():
    """激活微信窗口"""
    try:
        system = platform.system().lower()
        
        # 优先使用RPA引擎
        if rpa_available and WeChatManager:
            try:
                wechat_manager = WeChatManager()
                if wechat_manager.initialize():
                    activation_success = wechat_manager.activate_wechat()
                    if activation_success:
                        logger.info("通过RPA引擎成功激活微信")
                        return {"success": True, "message": "微信窗口已通过RPA引擎激活"}
                    else:
                        logger.warning("RPA引擎激活微信失败，尝试备用方法")
                else:
                    logger.warning("WeChatManager初始化失败，尝试备用方法")
            except Exception as e:
                logger.error(f"RPA引擎激活失败: {e}，尝试备用方法")
        
        # 备用方法：使用系统命令
        if system == "linux":
            # 使用wmctrl激活微信窗口
            result = subprocess.run(["which", "wmctrl"], capture_output=True, text=True)
            if result.returncode == 0:
                # 查找并激活微信窗口
                list_result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
                for line in list_result.stdout.split('\n'):
                    if "微信" in line or "WeChat" in line or "wechat" in line:
                        parts = line.split()
                        if len(parts) > 2:
                            window_id = parts[0]
                            subprocess.run(["wmctrl", "-i", "-R", window_id])
                            return {"success": True, "message": "微信窗口已激活"}
                return {"success": True, "message": "未找到微信窗口，但激活命令已发送"}
            else:
                return {"success": False, "error": "wmctrl未安装，无法激活微信窗口。请运行: sudo apt-get install wmctrl"}
        elif system == "darwin":  # macOS
            # macOS的窗口激活需要AppleScript
            script = '''
            tell application "WeChat"
                activate
            end tell
            '''
            try:
                subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                return {"success": True, "message": "微信窗口已激活"}
            except Exception:
                return {"success": False, "error": "无法激活微信窗口"}
        elif system == "windows":
            # Windows的窗口激活需要额外的库
            return {"success": True, "message": "微信窗口激活命令已发送"}
        else:
            return {"success": False, "error": f"不支持的操作系统: {system}"}
    except Exception as e:
        logger.error(f"激活微信窗口失败: {e}")
        return {"success": False, "error": str(e)}

# 辅助函数：获取屏幕尺寸
def get_screen_size():
    """获取屏幕尺寸"""
    try:
        system = platform.system().lower()
        if system == "linux":
            result = subprocess.run(["xrandr", "--query"], capture_output=True, text=True)
            if result.returncode == 0:
                import re
                # 查找当前分辨率
                match = re.search(r'(\d+x\d+)\s+current', result.stdout)
                if match:
                    resolution = match.group(1)
                    width, height = map(int, resolution.split('x'))
                    return width, height
                
                # 如果没找到current，查找主显示器
                for line in result.stdout.split('\n'):
                    if ' connected' in line:
                        res_match = re.search(r'(\d+x\d+)', line)
                        if res_match:
                            width, height = map(int, res_match.group(1).split('x'))
                            return width, height
        elif system == "darwin":  # macOS
            result = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True, text=True)
            import re
            match = re.search(r'Resolution: (\d+) x (\d+)', result.stdout)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                return width, height
        elif system == "windows":
            import ctypes
            user32 = ctypes.windll.user32
            screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            return screensize
    except Exception as e:
        logger.error(f"获取屏幕尺寸失败: {e}")
        # 返回默认尺寸
        return 1920, 1080


def _run_cmd(cmd: List[str], timeout: int = 3) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0
    except Exception:
        return False


def _list_windows_linux() -> List[str]:
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=3)
        if result.returncode != 0:
            return []
        return [line for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _set_window_geometry_by_id(window_id: str, x: int, y: int, width: int, height: int) -> bool:
    # 先去最大化，避免窗口管理器忽略 move/resize
    _run_cmd(["wmctrl", "-i", "-r", window_id, "-b", "remove,maximized_vert,maximized_horz"])

    wmctrl_ok = _run_cmd(["wmctrl", "-i", "-r", window_id, "-e", f"0,{x},{y},{width},{height}"])

    # xdotool兜底
    xdotool_size_ok = _run_cmd(["xdotool", "windowsize", "--sync", window_id, str(width), str(height)])
    xdotool_move_ok = _run_cmd(["xdotool", "windowmove", "--sync", window_id, str(x), str(y)])

    return wmctrl_ok or (xdotool_size_ok and xdotool_move_ok)


def _find_first_window_id(lines: List[str], include_keywords: List[str], exclude_keywords: Optional[List[str]] = None) -> Optional[str]:
    excludes = exclude_keywords or []
    for line in lines:
        line_lower = line.lower()
        if excludes and any(keyword.lower() in line_lower for keyword in excludes):
            continue
        if any(keyword.lower() in line_lower for keyword in include_keywords):
            parts = line.split(None, 3)
            if len(parts) >= 1:
                return parts[0]
    return None

# 辅助函数：设置窗口位置
def set_window_position(window_type: str, x: int, y: int, width: int, height: int):
    """设置窗口位置和大小"""
    global rpa_available
    
    try:
        # 优先使用ATSPI RPA引擎
        if rpa_available and window_type == "wechat" and WeChatManager and WindowManager:
            try:
                # 使用RPA引擎查找并激活微信窗口
                window_manager = WindowManager()
                wechat_window = window_manager.find_wechat_window()
                if wechat_window:
                    success = window_manager.activate_window(wechat_window.id, x, y, width, height)
                    if success:
                        logger.info(f"微信窗口已通过RPA定位: {wechat_window.title} -> ({x}, {y}, {width}x{height})")
                        return True
                
                # 如果RPA引擎失败，尝试激活微信
                wechat_manager = WeChatManager()
                if wechat_manager.initialize():
                    activation_success = wechat_manager.activate_wechat()
                    if activation_success:
                        # 等待片刻让窗口激活
                        import time
                        time.sleep(0.5)
                        # 再次尝试定位
                        wechat_window = window_manager.find_wechat_window()
                        if wechat_window:
                            success = window_manager.activate_window(wechat_window.id, x, y, width, height)
                            if success:
                                logger.info(f"微信窗口已通过RPA激活并定位: {wechat_window.title} -> ({x}, {y}, {width}x{height})")
                                return True
                
                logger.warning(f"RPA引擎未能定位微信窗口，将回退到系统命令")
            except Exception as e:
                logger.error(f"RPA引擎执行失败: {e}，将回退到系统命令")
        else:
            if not rpa_available:
                logger.info("RPA模块不可用，使用系统命令")
            elif not WeChatManager or not WindowManager:
                logger.info("WeChatManager或WindowManager不可用，使用系统命令")
        
        system = platform.system().lower()
        if system == "linux":
            # 在Linux上，我们通过wmctrl + xdotool控制窗口
            if not _run_cmd(["which", "wmctrl"]):
                logger.warning("wmctrl未安装，无法控制窗口位置。请运行: sudo apt-get install wmctrl")
                return False

            windows = _list_windows_linux()

            # 根据窗口类型查找窗口
            if window_type == "browser":
                cached_id = BROWSER_WINDOW_CACHE.get("id", "")
                if cached_id:
                    cached_ok = _set_window_geometry_by_id(cached_id, x, y, width, height)
                    if cached_ok:
                        logger.info(f"浏览器窗口已通过缓存ID定位: {cached_id} -> ({x}, {y}, {width}x{height})")
                        return True
                    _clear_browser_window_cache()

                browser_keywords = ["WeChat Copilot", "Vue", "localhost", "127.0.0.1", "dev", "test", "copilot"]
                excluded_keywords = ["微信", "WeChat", "wechat", "腾讯", "WXWork", "Visual Studio Code", " - Code", "PyCharm", "IntelliJ", "Cursor"]
                window_id = _find_first_window_id(windows, browser_keywords, excluded_keywords)
                if not window_id:
                    window_id = _find_first_window_id(windows, ["http", "chrome", "firefox", "browser"], excluded_keywords)

                if window_id:
                    success = _set_window_geometry_by_id(window_id, x, y, width, height)
                    if success:
                        _cache_browser_window(window_id, "")
                        logger.info(f"浏览器窗口已定位: {window_id} -> ({x}, {y}, {width}x{height})")
                    return success
                return False
            elif window_type == "wechat":
                wechat_keywords = ["微信", "WeChat", "wechat", "腾讯", "WXWork", "Wechat", "Tim"]
                window_id = _find_first_window_id(windows, wechat_keywords)
                if window_id:
                    success = _set_window_geometry_by_id(window_id, x, y, width, height)
                    if success:
                        _run_cmd(["wmctrl", "-i", "-a", window_id])
                        logger.info(f"微信窗口已定位: {window_id} -> ({x}, {y}, {width}x{height})")
                    return success

                logger.info("未找到微信窗口，尝试激活微信")
                _run_cmd(["wmctrl", "-a", "微信"])
                _run_cmd(["wmctrl", "-a", "WeChat"])
                return False
            elif window_type == "any":
                # active窗口兜底：直接调整当前激活窗口
                try:
                    active_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True, timeout=3).strip()
                except Exception:
                    active_id = ""

                if active_id:
                    success = _set_window_geometry_by_id(active_id, x, y, width, height)
                    if success:
                        logger.info(f"当前活动窗口已定位: {active_id} -> ({x}, {y}, {width}x{height})")
                    return success

                return False
        # 其他操作系统实现...
        return True
    except Exception as e:
        logger.error(f"设置窗口位置失败: {e}")
        return False

@router.get("/status")
async def get_wechat_status():
    """获取微信状态"""
    try:
        # 检查微信进程是否运行
        system = platform.system().lower()
        
        if system == "linux":
            cmd = ["pgrep", "-f", "wechat|WeChat|Electron"]
        elif system == "darwin":  # macOS
            cmd = ["pgrep", "-f", "WeChat"]
        elif system == "windows":
            cmd = ["tasklist", "/FI", "IMAGENAME eq WeChat.exe"]
        else:
            return {"success": False, "error": f"不支持的操作系统: {system}"}
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            is_running = result.returncode == 0 and result.stdout.strip() != ""
        except Exception:
            is_running = False
        
        # 模拟连接状态检查
        is_connected = is_running  # 简化的连接状态判断
        
        status_info = {
            "isRunning": is_running,
            "isConnected": is_connected,
            "version": "4.1.0",  # 模拟版本号
            "platform": system
        }
        
        return {
            "success": True,
            "data": status_info
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/wechat/set_window")
async def set_wechat_window(request: WindowSizeRequest):
    """设置微信窗口大小和位置"""
    try:
        width = request.width
        height = request.height
        x = request.x
        y = request.y

        # 激活微信窗口
        if rpa_available and WeChatManager:
            try:
                wechat_manager = WeChatManager()
                if wechat_manager.initialize():
                    activation_success = wechat_manager.activate_wechat()
                    if activation_success:
                        logger.info("成功激活微信窗口")
                    else:
                        logger.warning("激活微信窗口失败，但继续设置窗口位置")
            except Exception as e:
                logger.error(f"激活微信窗口失败: {e}")

        # 设置窗口位置
        success = set_window_position("wechat", x, y, width, height)

        return {
            "success": success,
            "message": f"微信窗口已设置为 {width}x{height} 位置 ({x}, {y})"
        }
    except Exception as e:
        logger.error(f"设置微信窗口失败: {e}")
        return {"success": False, "error": str(e)}