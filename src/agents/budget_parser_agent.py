"""
預算解析子Agent，專門負責解析查詢中的預算範圍
"""

from typing import Any

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent
from src.services.duckling_service import duckling_service


class BudgetParserAgent(BaseSubAgent):
    """預算解析子Agent"""

    def __init__(self):
        """初始化預算解析子Agent"""
        super().__init__("BudgetParserAgent")

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的預算範圍"""
        logger.info(f"解析查詢中的字串: {query}")

        # 使用 Duckling 服務提取預算
        try:
            budget = await duckling_service.extract_budget(query)

            # 驗證預算的有效性
            self._validate_budget(budget)
        except Exception as e:
            logger.error(f"使用 Duckling 服務提取預算時發生錯誤: {e}")
            budget = {"min": None, "max": None}

        return {"budget": budget}

    def _validate_budget(self, budget: dict[str, int]) -> None:
        """驗證預算的有效性"""
        # 如果最低價格大於最高價格，交換它們
        if budget["min"] is not None and budget["max"] is not None and budget["min"] > budget["max"]:
            logger.warning(f"最低價格 {budget['min']} 大於最高價格 {budget['max']}，交換它們")
            budget["min"], budget["max"] = budget["max"], budget["min"]

        # 如果最低價格小於0，設置為0
        if budget["min"] is not None and budget["min"] < 0:
            logger.warning(f"最低價格 {budget['min']} 小於0，設置為0")
            budget["min"] = 0

        # 如果最高價格小於0，設置為None
        if budget["max"] is not None and budget["max"] < 0:
            logger.warning(f"最高價格 {budget['max']} 小於0，設置為None")
            budget["max"] = None


# 創建預算解析子Agent實例
budget_parser_agent = BudgetParserAgent()
