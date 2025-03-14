"""
基礎Agent類，所有Agent都繼承自此類
"""

from typing import Any

from loguru import logger


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
