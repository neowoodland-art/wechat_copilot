import re
from typing import Dict, Any


class KeywordIntentDetector:
    def __init__(self):
        # 定义关键词和对应的意图
        self.intent_keywords = {
            "complex_task": [
                "编程", "计算", "数学", "代码", "算法", "技术", "复杂", "解决", "分析", "实现",
                "设计", "开发", "逻辑", "推理", "公式", "函数", "类", "方法", "调试", "优化"
            ],
            "special_skill": [
                "技能", "特殊", "定制", "高级", "专业", "专家", "技巧", "窍门", "攻略", "策略",
                "计划", "方案", "建议", "咨询", "指导", "教程", "指南", "秘诀", "绝招", "创新"
            ],
            "normal_conversation": [
                "你好", "嗨", "谢谢", "帮助", "聊天", "聊聊", "说说", "问问", "故事", "天气",
                "今天", "早上", "晚上", "吃饭", "工作", "生活", "心情", "感觉", "想法", "看法"
            ]
        }
    
    def classify_intent(self, text: str) -> str:
        """根据文本内容分类意图"""
        text_lower = text.lower()
        scores = {"complex_task": 0, "special_skill": 0, "normal_conversation": 0}
        
        # 计算每个意图的得分
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[intent] += 1
        
        # 返回得分最高的意图
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # 默认为普通对话
        return "normal_conversation"