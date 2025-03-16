"""
基礎Agent類，所有Agent都繼承自此類
"""

import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import orjson
from loguru import logger

# 使用延遲導入，避免循環導入問題
# from src.services.llm_service import llm_service

# 定義泛型類型，用於表示 LLM 提取的結果類型
T = TypeVar("T")


class BaseAgent(ABC):
    """基礎Agent類"""

    def __init__(self, name: str):
        """初始化基礎Agent"""
        self.name = name
        # 延遲導入 llm_service
        from src.services.llm_service import llm_service

        self.llm_service = llm_service
        logger.info(f"初始化Agent: {name}")

    @abstractmethod
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        處理輸入狀態，子類必須實現此方法

        Args:
            state: 輸入狀態字典

        Returns:
            處理結果
        """

    async def _extract_with_llm(self, prompt: str, system_prompt: str) -> dict[str, Any]:
        """
        使用LLM提取信息

        Args:
            prompt: 提示詞
            system_prompt: 系統提示詞

        Returns:
            LLM提取的結果
        """
        try:
            # 構建消息
            messages = [{"role": "user", "content": prompt}]

            # 調用LLM服務
            response = await self.llm_service.generate_response(messages, system_prompt)

            # 嘗試解析JSON響應
            try:
                # 使用正則表達式提取JSON部分
                json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response

                # 解析JSON
                result = orjson.loads(json_str)
                return result
            except Exception as e:
                logger.error(f"[{self.name}] 解析LLM響應失敗: {e}")
                return {"error": str(e)}

        except Exception as e:
            logger.error(f"[{self.name}] LLM提取失敗: {e}")
            return {"error": str(e)}
