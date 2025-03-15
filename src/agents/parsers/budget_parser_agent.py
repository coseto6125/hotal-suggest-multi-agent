"""
預算解析子Agent，專門負責解析查詢中的預算範圍
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent


class BudgetParserAgent(BaseSubAgent):
    """預算解析子Agent"""

    def __init__(self):
        """初始化預算解析子Agent"""
        super().__init__("BudgetParserAgent")
        # 預算正則表達式模式
        self.price_range_patterns = [
            # 範圍格式：X-Y元/塊/NT$/台幣
            re.compile(
                r"(\d+(?:,\d+)?)\s*(?:-|~|到)\s*(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)?(?:/晚|每晚|一晚)?"
            ),
            # 最低價格格式：最低X元/塊/NT$/台幣
            re.compile(r"(?:最低|至少|起碼)\s*(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)(?:/晚|每晚|一晚)?"),
            # 最高價格格式：最高X元/塊/NT$/台幣
            re.compile(r"(?:最高|最多|不超過)\s*(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)(?:/晚|每晚|一晚)?"),
            # 單一價格格式：X元/塊/NT$/台幣左右/上下
            re.compile(r"(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)(?:/晚|每晚|一晚)?(?:左右|上下)"),
            # 單一價格格式：X元/塊/NT$/台幣
            re.compile(r"(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)(?:/晚|每晚|一晚)?"),
        ]

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的預算"""
        logger.debug(f"[{self.name}] 開始解析預算")
        try:
            if not query:
                raise ValueError("查詢內容為空")

            # 使用正則表達式解析預算
            budget = self._extract_budget_with_regex(query)

            # 如果無法解析，返回空值
            if not budget.get("amount"):
                logger.info("無法解析預算金額，設置為空值")
                return {"amount": None, "message": "無法從查詢中提取預算金額"}

            return budget

        except Exception as e:
            logger.error(f"[{self.name}] 預算解析失敗: {e}")
            return {"amount": None, "message": f"預算解析失敗（錯誤：{e!s}）"}

    def _extract_budget_with_regex(self, query: str) -> dict[str, Any]:
        """使用正則表達式從查詢中提取預算"""
        # 預算金額正則表達式模式
        amount_pattern = r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:萬|k|K|千|元|塊|NTD|TWD|台幣|新台幣)?"

        # 查找預算金額
        amount_match = re.search(amount_pattern, query)
        if not amount_match:
            return {"amount": None}

        # 提取金額
        amount_str = amount_match.group(1).replace(",", "")
        try:
            amount = float(amount_str)
        except ValueError:
            return {"amount": None}

        # 檢查是否為萬元單位
        if "萬" in query:
            amount *= 10000

        # 檢查是否為千元單位
        if "k" in query.lower() or "千" in query:
            amount *= 1000

        return {"amount": int(amount)}

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
