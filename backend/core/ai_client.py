import asyncio
import aiohttp
from typing import Dict, Any, List
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("QWEN_API_KEY")
        self.model = os.getenv("LLM_MODEL", "qwen-max")
        self.base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")
    
    async def call(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        """调用大模型 API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "temperature": temperature
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                if "aliyuncs.com" in self.base_url:
                    # 阿里云通义千问 API 格式
                    url = f"{self.base_url}/services/aigc/text-generation/generation"
                else:
                    url = f"{self.base_url}/v1/chat/completions"
                
                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()
                    
                    if "aliyuncs.com" in self.base_url:
                        # 阿里云响应格式
                        text = result.get("output", {}).get("text", "")
                    else:
                        # OpenAI 格式
                        text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    return {
                        "success": True,
                        "response": text,
                        "raw": result
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "response": "抱歉，AI服务暂时不可用，请稍后再试。"
                }
    
    async def generate_summary(self, user_nickname: str, messages: List[str]) -> Dict[str, Any]:
        """生成用户聊天总结"""
        content = "\\n".join(messages[-10:])  # 最近10条消息
        prompt = f"""你是客服分析师。请分析客户 {user_nickname} 的聊天记录，生成简洁总结和标签。

聊天记录：
{content}

请输出JSON格式：
{{"summary": "客户核心诉求总结", "tags": ["标签1", "标签2"]}}"""

        return await self.call(prompt, temperature=0.3)

# 全局实例
ai_client = AIClient()

class MultimodalAIClient:
    def __init__(self):
        self.api_key = os.getenv("MULTIMODAL_API_KEY")
        self.base_url = os.getenv("MULTIMODAL_BASE_URL", "https://api.openai.com/v1/chat/completions")
        self.model = os.getenv("MULTIMODAL_MODEL", "gpt-4-vision-preview")
    
    async def analyze_ui_elements(self, image_path: str) -> Dict[str, Any]:
        """分析UI界面元素"""
        try:
            if not self.api_key:
                return {"success": False, "error": "未配置多模态API密钥"}
            
            # 读取图像文件
            import base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请分析这张微信聊天界面的截图，识别出界面元素（如消息区域、输入框、按钮等），并返回JSON格式的分析结果。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/chat/completions", 
                                      headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # 尝试解析JSON响应
            try:
                analysis_result = json.loads(content)
                return {"success": True, "elements": analysis_result}
            except json.JSONDecodeError:
                logger.error(f"无法解析多模态AI返回的JSON: {content}")
                return {"success": False, "error": "无法解析AI返回结果"}
        
        except Exception as e:
            logger.error(f"多模态AI分析UI元素失败: {e}")
            return {"success": False, "error": str(e)}

multimodal_ai_client = MultimodalAIClient()

class MultimodalAIClient:
    def __init__(self):
        self.api_key = os.getenv("MULTIMODAL_API_KEY")
        self.base_url = os.getenv("MULTIMODAL_BASE_URL", "https://api.openai.com/v1/chat/completions")
        self.model = os.getenv("MULTIMODAL_MODEL", "gpt-4-vision-preview")
    
    async def analyze_ui_elements(self, image_path: str) -> Dict[str, Any]:
        """分析UI界面元素"""
        try:
            if not self.api_key:
                return {"success": False, "error": "未配置多模态API密钥"}
            
            # 读取图像文件
            import base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请分析这张微信聊天界面的截图，识别出界面元素（如消息区域、输入框、按钮等），并返回JSON格式的分析结果。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/chat/completions", 
                                      headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # 尝试解析JSON响应
            try:
                analysis_result = json.loads(content)
                return {"success": True, "elements": analysis_result}
            except json.JSONDecodeError:
                logger.error(f"无法解析多模态AI返回的JSON: {content}")
                return {"success": False, "error": "无法解析AI返回结果"}
        
        except Exception as e:
            logger.error(f"多模态AI分析UI元素失败: {e}")
            return {"success": False, "error": str(e)}

multimodal_ai_client = MultimodalAIClient()