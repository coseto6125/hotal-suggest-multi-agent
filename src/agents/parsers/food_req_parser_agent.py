"""
食物需求解析子Agent，專門負責解析查詢中的餐食需求
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent


class FoodReqParserAgent(BaseSubAgent):
    """食物需求解析子Agent"""

    def __init__(self):
        """初始化食物需求解析子Agent"""
        super().__init__("FoodReqParserAgent")
        # TODO: 定義餐食需求相關的正則表達式模式
        self.breakfast_patterns = [
            re.compile(r"(?:早餐|早點|早飯|早上吃的|含早|供應早餐|提供早餐|有早餐|要早餐)"),
            re.compile(r"(?:不要早餐|不含早餐|不需要早餐|沒有早餐)"),
        ]

        self.lunch_patterns = [
            re.compile(r"(?:午餐|午飯|中餐|中午吃的|含午|供應午餐|提供午餐|有午餐|要午餐)"),
            re.compile(r"(?:不要午餐|不含午餐|不需要午餐|沒有午餐)"),
        ]

        self.dinner_patterns = [
            re.compile(r"(?:晚餐|晚飯|晚上吃的|含晚|供應晚餐|提供晚餐|有晚餐|要晚餐)"),
            re.compile(r"(?:不要晚餐|不含晚餐|不需要晚餐|沒有晚餐)"),
        ]

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的餐食需求"""
        logger.info(f"解析查詢中的餐食需求: {query}")

        # TODO: 實現餐食需求解析邏輯
        # 嘗試使用正則表達式解析餐食需求
        food_req = self._extract_food_req_with_regex(query)

        return {"food_req": food_req}

    def _extract_food_req_with_regex(self, query: str) -> dict[str, bool]:
        """使用正則表達式從查詢中提取餐食需求"""
        # TODO: 實現正則表達式解析餐食需求的邏輯
        food_req = {"has_breakfast": False, "has_lunch": False, "has_dinner": False}

        # 檢查早餐需求
        for pattern in self.breakfast_patterns:
            if pattern.search(query):
                # 檢查是否是否定表達
                if "不" in query or "沒" in query:
                    food_req["has_breakfast"] = False
                else:
                    food_req["has_breakfast"] = True
                logger.debug(f"從查詢中提取到早餐需求: {food_req['has_breakfast']}")
                break

        # 檢查午餐需求
        for pattern in self.lunch_patterns:
            if pattern.search(query):
                # 檢查是否是否定表達
                if "不" in query or "沒" in query:
                    food_req["has_lunch"] = False
                else:
                    food_req["has_lunch"] = True
                logger.debug(f"從查詢中提取到午餐需求: {food_req['has_lunch']}")
                break

        # 檢查晚餐需求
        for pattern in self.dinner_patterns:
            if pattern.search(query):
                # 檢查是否是否定表達
                if "不" in query or "沒" in query:
                    food_req["has_dinner"] = False
                else:
                    food_req["has_dinner"] = True
                logger.debug(f"從查詢中提取到晚餐需求: {food_req['has_dinner']}")
                break

        return food_req


# 創建食物需求解析子Agent實例
food_req_parser_agent = FoodReqParserAgent()
