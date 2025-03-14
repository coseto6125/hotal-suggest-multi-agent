"""
基礎子Agent類，所有專門的子Agent都繼承自此類
"""

from typing import Any

from loguru import logger

from src.agents.base_agent import BaseAgent


class BaseSubAgent(BaseAgent):
    """基礎子Agent類"""

    def __init__(self, name: str):
        """初始化基礎子Agent"""
        super().__init__(name)
        logger.info(f"初始化子Agent: {name}")

    async def process_query(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """處理查詢，由子類實現"""
        if context is None:
            context = {}

        try:
            return await self._process_query(query, context)
        except Exception as e:
            logger.error(f"子Agent {self.name} 處理查詢失敗: {e!s}")
            return {"error": str(e)}

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢，由子類實現"""
        raise NotImplementedError("子類必須實現_process_query方法")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """實現BaseAgent的_process方法"""
        query = inputs.get("user_query", "")
        context = inputs.get("context", {})
        return await self.process_query(query, context)
