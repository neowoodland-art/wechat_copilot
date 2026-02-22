import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib


class CacheManager:
    def __init__(self, cache_dir: str = "./cache", cache_ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = cache_ttl  # 缓存生存时间（秒）
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_file_path(self) -> Path:
        return self.cache_dir / "ui_elements_cache.json"
    
    def _get_timestamp_file_path(self) -> Path:
        return self.cache_dir / "ui_elements_timestamp.txt"
    
    def save_elements(self, elements: Dict[str, Any]) -> bool:
        """保存UI元素到缓存"""
        try:
            cache_file = self._get_cache_file_path()
            timestamp_file = self._get_timestamp_file_path()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            
            with open(timestamp_file, 'w') as f:
                f.write(str(int(time.time())))
            
            return True
        except Exception as e:
            print(f"保存缓存失败: {e}")
            return False
    
    def load_elements(self) -> Dict[str, Any]:
        """从缓存加载UI元素"""
        try:
            cache_file = self._get_cache_file_path()
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载缓存失败: {e}")
            return {}
    
    def is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        timestamp_file = self._get_timestamp_file_path()
        if not timestamp_file.exists():
            return False
        
        try:
            with open(timestamp_file, 'r') as f:
                timestamp = int(f.read().strip())
            
            current_time = int(time.time())
            return (current_time - timestamp) < self.cache_ttl
        except:
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        timestamp_file = self._get_timestamp_file_path()
        if timestamp_file.exists():
            try:
                with open(timestamp_file, 'r') as f:
                    timestamp = int(f.read().strip())
                return {
                    "timestamp": timestamp,
                    "valid": self.is_cache_valid(),
                    "age_seconds": int(time.time()) - timestamp
                }
            except:
                pass
        
        return {"timestamp": None, "valid": False, "age_seconds": 0}