"""
基礎Agent類，所有Agent都繼承自此類
"""

import re
from abc import ABC, abstractmethod
from typing import Any

import orjson
from loguru import logger


class BaseAgent(ABC):
    """基礎Agent類"""

    def __init__(self, name: str):
        """初始化基礎Agent"""
        self.name = name
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
            # 延遲導入 llm_agent 避免循環引用
            from src.agents.generators.llm_agent import llm_agent

            # 構建消息
            messages = [{"role": "user", "content": prompt}]

            # 設置請求狀態
            llm_request = {
                "llm_request_type": "generate_response",
                "messages": messages,
                "system_prompt": system_prompt,
            }

            # 調用LLM Agent
            response_state = await llm_agent.process(llm_request)
            response = response_state.get("response", "")

            # 嘗試解析JSON響應
            try:
                # 使用正則表達式提取JSON部分
                json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
                json_str = json_match.group(1) if json_match else response

                # 解析JSON
                result = orjson.loads(json_str)
                return result
            except Exception as e:
                logger.error(f"[{self.name}] 解析LLM響應失敗: {e}")
                return {"error": str(e)}

        except Exception as e:
            logger.error(f"[{self.name}] LLM提取失敗: {e}")
            return {"error": str(e)}
