"""
預算解析子Agent，專門負責解析查詢中的預算範圍
"""

import re
from typing import Any

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent


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
        """處理查詢中的預算範圍"""
        logger.info(f"解析查詢中的預算範圍: {query}")

        # 嘗試使用正則表達式解析預算
        budget = self._extract_budget_with_regex(query)

        # 如果正則表達式無法解析，使用LLM解析
        if budget["min"] is None and budget["max"] is None:
            llm_budget = await self._extract_budget_with_llm(query)

            # 合併結果
            if llm_budget["min"] is not None:
                budget["min"] = llm_budget["min"]
            if llm_budget["max"] is not None:
                budget["max"] = llm_budget["max"]

        # 驗證預算的有效性
        self._validate_budget(budget)

        return {"budget": budget}

    def _extract_budget_with_regex(self, query: str) -> dict[str, int]:
        """使用正則表達式從查詢中提取預算"""
        budget = {"min": None, "max": None}

        # 提取價格範圍
        for pattern in self.price_range_patterns:
            match = pattern.search(query)
            if match:
                try:
                    # 處理不同的匹配情況
                    if len(match.groups()) == 2:  # 範圍格式
                        min_price = int(match.group(1).replace(",", ""))
                        max_price = int(match.group(2).replace(",", ""))
                        budget["min"] = min_price
                        budget["max"] = max_price
                        logger.debug(f"從查詢中提取到價格範圍: {min_price}-{max_price}")
                    elif (
                        "最低" in match.string[match.start() : match.end()]
                        or "至少" in match.string[match.start() : match.end()]
                        or "起碼" in match.string[match.start() : match.end()]
                    ):
                        # 最低價格格式
                        min_price = int(match.group(1).replace(",", ""))
                        budget["min"] = min_price
                        logger.debug(f"從查詢中提取到最低價格: {min_price}")
                    elif (
                        "最高" in match.string[match.start() : match.end()]
                        or "最多" in match.string[match.start() : match.end()]
                        or "不超過" in match.string[match.start() : match.end()]
                    ):
                        # 最高價格格式
                        max_price = int(match.group(1).replace(",", ""))
                        budget["max"] = max_price
                        logger.debug(f"從查詢中提取到最高價格: {max_price}")
                    elif (
                        "左右" in match.string[match.start() : match.end()]
                        or "上下" in match.string[match.start() : match.end()]
                    ):
                        # 單一價格左右格式
                        price = int(match.group(1).replace(",", ""))
                        budget["min"] = int(price * 0.8)  # 下浮20%
                        budget["max"] = int(price * 1.2)  # 上浮20%
                        logger.debug(f"從查詢中提取到價格左右: {price}，範圍: {budget['min']}-{budget['max']}")
                    else:
                        # 單一價格格式，視為最高價格
                        price = int(match.group(1).replace(",", ""))
                        budget["max"] = price
                        logger.debug(f"從查詢中提取到單一價格: {price}，視為最高價格")
                    break
                except (ValueError, IndexError):
                    continue

        return budget

    async def _extract_budget_with_llm(self, query: str) -> dict[str, int]:
        """使用LLM從查詢中提取預算"""
        system_prompt = """
        你是一個旅館預訂系統的預算解析器。
        你的任務是從用戶的自然語言查詢中提取預算範圍。
        請返回整數值，單位為新台幣。
        如果查詢中只提到一個價格，請根據上下文判斷是最低價格還是最高價格。
        如果查詢中沒有明確提到價格，請返回null。
        
        請以JSON格式返回結果，格式如下：
        {
            "min": 最低價格,
            "max": 最高價格
        }
        """

        user_message_template = "從以下查詢中提取預算範圍：{query}"
        default_value = {"min": None, "max": None}

        # 使用共用方法提取預算
        return await self._extract_with_llm(
            query=query,
            system_prompt=system_prompt,
            user_message_template=user_message_template,
            default_value=default_value,
        )

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
