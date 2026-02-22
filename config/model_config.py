# 模型配置文件

# 多模态模型配置（用于UI分析）
multimodal_model_config = {
    'model': 'gpt-4-vision-preview',  # 或其他支持视觉的模型
    'api_key': '',  # 在环境变量中设置 MULTIMODAL_API_KEY
    'base_url': 'https://api.openai.com/v1/chat/completions',
    'enabled': True,
    'temperature': 0.1,
    'max_tokens': 1000
}

# 本地LLM配置（用于普通对话）
local_llm_config = {
    'model': 'qwen2:0.5b',  # Ollama模型名称
    'base_url': 'http://localhost:11434/api/generate',
    'enabled': True,
    'temperature': 0.7,
    'max_tokens': 500
}

# 豆包大模型配置（用于特殊技能）
doubao_llm_config = {
    'model': 'doubao-pro',  # 豆包模型标识
    'api_key': '',  # 在环境变量中设置 DOUBAO_API_KEY
    'base_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    'enabled': True,
    'temperature': 0.5,
    'max_tokens': 1000
}

# 阿里大模型配置（用于复杂任务）
alibaba_llm_config = {
    'model': 'qwen-max',  # 通义千问Max版本
    'api_key': '',  # 在环境变量中设置 ALIBABA_API_KEY
    'base_url': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
    'enabled': True,
    'temperature': 0.6,
    'max_tokens': 2000
}

# 统一路由策略配置
llm_routing_config = {
    # 优先级：简单任务优先本地，复杂任务优先阿里，特殊技能优先豆包
    'intent_tier_map': {
        'normal_conversation': ['local', 'doubao'],
        'special_skill': ['doubao', 'local'],
        'complex_task': ['alibaba', 'doubao', 'local']
    },
    # 显式指定模型时的兜底链
    'preferred_fallback_map': {
        'local': ['local', 'doubao'],
        'doubao': ['doubao', 'local'],
        'alibaba': ['alibaba', 'doubao', 'local'],
        'auto': []
    },
    # 判定“无有效匹配”的文本关键词（命中则触发回退）
    'invalid_response_keywords': [
        '抱歉', '无法', '不支持', '未匹配', '请重试', '暂时不可用'
    ]
}