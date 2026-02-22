import logging
from typing import Dict, Any, List, Tuple
from config.model_config import (
    local_llm_config,
    doubao_llm_config,
    alibaba_llm_config,
    llm_routing_config,
)
from core.ai_client import LocalLLMClient, DoubaoLLMClient, AlibabaLLMClient
from core.intent_detector import KeywordIntentDetector

logger = logging.getLogger(__name__)

class AIRouter:
    def __init__(self):
        self.local_llm = LocalLLMClient(local_llm_config)
        self.doubao_llm = DoubaoLLMClient(doubao_llm_config)
        self.alibaba_llm = AlibabaLLMClient(alibaba_llm_config)
        self.keyword_detector = KeywordIntentDetector()
        self.routing_config = llm_routing_config

    def _get_client(self, model_name: str):
        if model_name == "local":
            return self.local_llm, local_llm_config
        if model_name == "doubao":
            return self.doubao_llm, doubao_llm_config
        if model_name == "alibaba":
            return self.alibaba_llm, alibaba_llm_config
        return None, {}

    def _is_model_enabled(self, model_name: str) -> bool:
        _, config = self._get_client(model_name)
        return bool(config.get("enabled", True))

    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        if not result or not bool(result.get("success", False)):
            return False

        text = str(result.get("response", "") or "").strip()
        if not text:
            return False

        bad_words = self.routing_config.get("invalid_response_keywords", [])
        lowered = text.lower()
        if any(str(word).lower() in lowered for word in bad_words):
            return False

        return True

    def _build_chain(self, intent: str, preferred_model: str) -> List[str]:
        preferred = (preferred_model or "auto").strip().lower()
        pref_map = self.routing_config.get("preferred_fallback_map", {})
        if preferred in pref_map and pref_map.get(preferred):
            chain = list(pref_map.get(preferred, []))
        else:
            chain = list(self.routing_config.get("intent_tier_map", {}).get(intent, ["local", "doubao"]))

        # 去重且保持顺序
        seen = set()
        deduped = []
        for item in chain:
            if item not in seen:
                deduped.append(item)
                seen.add(item)

        # 最低保障：local / doubao 二选一至少尝试一个可用项
        if "local" not in seen:
            deduped.append("local")
            seen.add("local")
        if "doubao" not in seen:
            deduped.append("doubao")

        return deduped

    async def _call_with_fallback(self, text: str, context: Dict[str, Any], chain: List[str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        trace: List[Dict[str, Any]] = []
        last_result: Dict[str, Any] = {"success": False, "response": "", "error": "no_result"}

        for model_name in chain:
            if not self._is_model_enabled(model_name):
                trace.append({"model": model_name, "status": "skipped", "reason": "disabled"})
                continue

            client, _ = self._get_client(model_name)
            if client is None:
                trace.append({"model": model_name, "status": "skipped", "reason": "unknown_model"})
                continue

            result = await client.call(text, context)
            last_result = result

            if self._is_valid_result(result):
                result["model_used"] = model_name
                trace.append({"model": model_name, "status": "success"})
                return result, trace

            trace.append({
                "model": model_name,
                "status": "failed",
                "error": str(result.get("error", "invalid_or_empty_response")),
            })

        # 兜底：如果链路都失败，至少返回最后一次结果（若仍为空，给标准降级文案）
        if not last_result.get("response"):
            last_result["response"] = "抱歉，当前模型服务暂不可用，请稍后重试。"
        last_result["success"] = False
        last_result["model_used"] = "fallback_failed"
        return last_result, trace
    
    async def route_request(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """按意图分级路由并做容错回退。

        规则：
        - 普通任务：local -> doubao
        - 特殊技能：doubao -> local
        - 复杂任务：alibaba -> doubao -> local
        - 显式指定 model_preference 时优先按指定链路
        """
        context = context or {}
        intent = self.keyword_detector.classify_intent(text)
        preferred_model = str(context.get("model_preference", "auto") or "auto").lower()

        chain = self._build_chain(intent=intent, preferred_model=preferred_model)
        result, trace = await self._call_with_fallback(text=text, context=context, chain=chain)

        result["routing_intent"] = intent
        result["routing_chain"] = chain
        result["routing_trace"] = trace
        result["fallback_used"] = len([item for item in trace if item.get("status") == "failed"]) > 0
        return result