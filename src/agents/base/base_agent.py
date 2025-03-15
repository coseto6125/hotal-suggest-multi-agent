"""
基礎Agent類，所有Agent都繼承自此類
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from loguru import logger

from src.services.llm_service import llm_service

# 定義泛型類型，用於表示 LLM 提取的結果類型
T = TypeVar("T")


class BaseAgent(ABC):
    """基礎Agent類"""

    def __init__(self, name: str):
        """初始化基礎Agent"""
        self.name = name
        self.llm_service = llm_service
        logger.info(f"初始化Agent: {name}")

    async def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """運行Agent"""
        logger.info(f"運行Agent: {self.name}")
        try:
            return await self._process(inputs)
        except Exception as e:
            logger.error(f"Agent {self.name} 運行失敗: {e!s}")
            return {"error": str(e)}

    @abstractmethod
    async def _process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理狀態"""

    async def _extract_with_llm(
        self, prompt: str, system_prompt: str, response_format: dict[str, Any]
    ) -> dict[str, Any]:
        """使用 LLM 提取資訊"""
        try:
            # 構建消息
            messages = [{"role": "user", "content": prompt}]

            # 生成回應
            response = await self.llm_service.generate_response(messages=messages, system_prompt=system_prompt)

            # 檢查回應格式
            if not isinstance(response, dict):
                logger.debug(f"[{self.name}] LLM回應不是JSON格式，返回原始回應: {response}")
                return {"response": response}

            return response
        except Exception as e:
            logger.error(f"[{self.name}] LLM提取失敗: {e}")
            return {"error": str(e)}
