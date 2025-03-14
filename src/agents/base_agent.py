"""
基礎Agent類，所有Agent都繼承自此類
"""

import re
from typing import Any, TypeVar

import orjson
from loguru import logger

from src.services.llm_service import llm_service

# 定義泛型類型，用於表示 LLM 提取的結果類型
T = TypeVar("T")


class BaseAgent:
    """基礎Agent類"""

    def __init__(self, name: str):
        """初始化基礎Agent"""
        self.name = name
        logger.info(f"初始化Agent: {name}")

    async def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """運行Agent"""
        logger.info(f"運行Agent: {self.name}")
        try:
            return await self._process(inputs)
        except Exception as e:
            logger.error(f"Agent {self.name} 運行失敗: {e!s}")
            return {"error": str(e)}

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理輸入，由子類實現"""
        raise NotImplementedError("子類必須實現_process方法")

    async def _extract_with_llm(
        self,
        query: str,
        system_prompt: str,
        user_message_template: str = "從以下查詢中提取信息：{query}",
        default_value: T = None,
    ) -> T:
        """
        使用LLM從查詢中提取信息的通用方法

        Args:
            query: 用戶查詢字符串
            system_prompt: 系統提示，指導LLM如何處理查詢
            user_message_template: 用戶消息模板，可以包含{query}佔位符
            default_value: 如果LLM提取失敗時返回的默認值

        Returns:
            提取的信息，如果提取失敗則返回默認值
        """
        # 格式化用戶消息
        user_message = user_message_template.format(query=query)

        # 創建消息列表
        messages = [{"role": "user", "content": user_message}]

        try:
            # 調用LLM服務
            response = await llm_service.generate_response(messages, system_prompt)

            # 使用正則表達式提取JSON
            json_pattern = re.compile(r"{.*}", re.DOTALL)
            match = json_pattern.search(response)

            if match:
                # 解析JSON
                result = orjson.loads(match.group(0))
                logger.debug(f"LLM提取成功: {result}")
                return result
            # 如果沒有找到JSON，嘗試直接解析整個回應
            try:
                result = orjson.loads(response)
                logger.debug(f"LLM提取成功(整個回應): {result}")
                return result
            except Exception:
                # 如果不是JSON格式，則返回原始回應（適用於單值提取）
                logger.debug(f"LLM回應不是JSON格式，返回原始回應: {response}")
                return response.strip()

        except Exception as e:
            logger.error(f"LLM提取失敗: {e!s}")
            return default_value
