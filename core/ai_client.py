import os
import json
import logging
import requests
import aiohttp
from typing import Dict, Any, Optional
from config.model_config import multimodal_model_config, local_llm_config, doubao_llm_config, alibaba_llm_config

class BaseLLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    async def call(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement call method")

class LocalLLMClient(BaseLLMClient):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434/api/generate')
        
    async def call(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            prompt_text = str(text or "")
            if context:
                prompt_text = f"上下文(JSON):\n{json.dumps(context, ensure_ascii=False)}\n\n用户请求:\n{prompt_text}"

            payload = {
                "model": self.config.get('model', 'qwen2:0.5b'),
                "prompt": prompt_text,
                "stream": False,
                "options": {
                    "temperature": self.config.get('temperature', 0.7),
                    "num_predict": self.config.get('max_tokens', 500)
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
            return {
                "response": result.get("response", ""),
                "success": True,
                "model_used": self.config.get('model', 'qwen2:0.5b')
            }
        except Exception as e:
            logger.error(f"本地LLM调用失败: {e}")
            return {"response": "", "success": False, "error": str(e)}

class DoubaoLLMClient(BaseLLMClient):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key', os.getenv('DOUBAO_API_KEY'))
        self.base_url = config.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
        
    async def call(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if not self.api_key:
                return {"response": "", "success": False, "error": "missing_doubao_api_key"}

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.config.get('model', 'doubao-pro'),
                "messages": [{"role": "user", "content": text}],
                "temperature": self.config.get('temperature', 0.5),
                "max_tokens": self.config.get('max_tokens', 1000)
            }
            
            if context:
                # 添加上下文到消息中
                payload["messages"].insert(0, {"role": "system", "content": json.dumps(context)})
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
            return {
                "response": result['choices'][0]['message']['content'],
                "success": True,
                "model_used": self.config.get('model', 'doubao-pro')
            }
        except Exception as e:
            logger.error(f"豆包LLM调用失败: {e}")
            return {"response": "", "success": False, "error": str(e)}

class AlibabaLLMClient(BaseLLMClient):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key', os.getenv('ALIBABA_API_KEY'))
        self.base_url = config.get('base_url', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
        
    async def call(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if not self.api_key:
                return {"response": "", "success": False, "error": "missing_alibaba_api_key"}

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "X-DashScope-SSE": "disable"  # 禁用流式响应
            }
            
            payload = {
                "model": self.config.get('model', 'qwen-max'),
                "input": {
                    "messages": [
                        {"role": "system", "content": "你是一个高级AI助手，能够处理复杂任务，包括编程、数学计算和逻辑推理。"},
                        {"role": "user", "content": text}
                    ]
                },
                "parameters": {
                    "temperature": self.config.get('temperature', 0.6),
                    "max_tokens": self.config.get('max_tokens', 2000)
                }
            }
            
            if context:
                # 添加上下文到系统消息
                payload["input"]["messages"][0]["content"] += f"\n上下文信息：{json.dumps(context)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
            return {
                "response": result['output']['text'],
                "success": True,
                "model_used": self.config.get('model', 'qwen-max')
            }
        except Exception as e:
            logger.error(f"阿里LLM调用失败: {e}")
            return {"response": "", "success": False, "error": str(e)}

logger = logging.getLogger(__name__)

class MultimodalAIClient:
    def __init__(self):
        self.api_key = multimodal_model_config.get('api_key', os.getenv('MULTIMODAL_API_KEY'))
        self.base_url = multimodal_model_config.get('base_url', 'https://api.openai.com/v1/chat/completions')
        self.model = multimodal_model_config.get('model', 'gpt-4-vision-preview')
    
    def analyze_ui_elements(self, image_path: str) -> Dict[str, Any]:
        """使用多模态AI分析UI元素"""
        try:
            # 读取图像并编码为base64
            with open(image_path, 'rb') as img_file:
                import base64
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请分析这张微信界面截图，识别出重要的UI元素（如聊天框、输入框、发送按钮、联系人列表等），并返回每个元素的坐标(x, y)、宽度(width)、高度(height)和类型(type)。请以JSON格式返回，格式为：{\"elements\": {\"element_name\": {\"x\": int, \"y\": int, \"width\": int, \"height\": int, \"type\": \"button/text_area/etc\"}}}. 只返回JSON数据，不要其他解释。"
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
            
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析返回的JSON
            try:
                parsed_result = json.loads(content)
                return {"success": True, "elements": parsed_result["elements"]}
            except json.JSONDecodeError:
                logger.error(f"无法解析多模态AI返回的JSON: {content}")
                return {"success": False, "error": "无法解析AI返回结果"}
        
        except Exception as e:
            logger.error(f"多模态AI分析UI元素失败: {e}")
            return {"success": False, "error": str(e)}


import json
import logging
import requests
from typing import Dict, Any, Optional
from config.model_config import multimodal_model_config

logger = logging.getLogger(__name__)

class MultimodalAIClient:
    def __init__(self):
        self.api_key = multimodal_model_config.get('api_key', os.getenv('MULTIMODAL_API_KEY'))
        self.base_url = multimodal_model_config.get('base_url', 'https://api.openai.com/v1/chat/completions')
        self.model = multimodal_model_config.get('model', 'gpt-4-vision-preview')
    
    def analyze_ui_elements(self, image_path: str) -> Dict[str, Any]:
        """使用多模态AI分析UI元素"""
        try:
            # 读取图像并编码为base64
            with open(image_path, 'rb') as img_file:
                import base64
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请分析这张微信界面截图，识别出重要的UI元素（如聊天框、输入框、发送按钮、联系人列表等），并返回每个元素的坐标(x, y)、宽度(width)、高度(height)和类型(type)。请以JSON格式返回，格式为：{\"elements\": {\"element_name\": {\"x\": int, \"y\": int, \"width\": int, \"height\": int, \"type\": \"button/text_area/etc\"}}}. 只返回JSON数据，不要其他解释。"
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
            
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析返回的JSON
            try:
                parsed_result = json.loads(content)
                return {"success": True, "elements": parsed_result["elements"]}
            except json.JSONDecodeError:
                logger.error(f"无法解析多模态AI返回的JSON: {content}")
                return {"success": False, "error": "无法解析AI返回结果"}
        
        except Exception as e:
            logger.error(f"多模态AI分析UI元素失败: {e}")
            return {"success": False, "error": str(e)}