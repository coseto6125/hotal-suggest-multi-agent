"""
食物需求解析子Agent，專門負責解析查詢中的餐食需求
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent


class FoodReqParserAgent(BaseAgent):
    """食物需求解析子Agent"""

    def __init__(self):
        """初始化食物需求解析子Agent"""
        super().__init__("FoodReqParserAgent")
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

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理餐食需求解析請求"""
        logger.debug(f"[{self.name}] 開始處理餐食需求解析請求")

        # 從輸入中提取查詢和上下文
        query = state.get("query", "")
        context = state.get("context", {})

        try:
            if not query:
                # 如果沒有查詢文本，嘗試從上下文或其他字段獲取信息
                if "food_req" in context:
                    return {"food_req": context["food_req"]}

                logger.warning("查詢內容為空，無法解析餐食需求")
                return {"food_req": {"has_breakfast": False, "has_lunch": False, "has_dinner": False}}

            # 使用正則表達式解析餐食需求
            food_req = self._extract_food_req_with_regex(query)

            return {"food_req": food_req}

        except Exception as e:
            logger.error(f"[{self.name}] 餐食需求解析失敗: {e}")
            return {
                "food_req": {"has_breakfast": False, "has_lunch": False, "has_dinner": False},
                "message": f"餐食需求解析失敗（錯誤：{e!s}）",
            }

    def _extract_food_req_with_regex(self, query: str) -> dict[str, bool]:
        """使用正則表達式從查詢中提取餐食需求"""
        food_req = {"has_breakfast": False, "has_lunch": False, "has_dinner": False}

        # 檢查早餐需求
        for pattern in self.breakfast_patterns:
            match = pattern.search(query)
            if match:
                # 檢查是否是否定表達
                matched_text = match.group(0)
                if "不" in matched_text or "沒" in matched_text:
                    food_req["has_breakfast"] = False
                else:
                    food_req["has_breakfast"] = True
                logger.debug(f"從查詢中提取到早餐需求: {food_req['has_breakfast']}")
                break

        # 檢查午餐需求
        for pattern in self.lunch_patterns:
            match = pattern.search(query)
            if match:
                # 檢查是否是否定表達
                matched_text = match.group(0)
                if "不" in matched_text or "沒" in matched_text:
                    food_req["has_lunch"] = False
                else:
                    food_req["has_lunch"] = True
                logger.debug(f"從查詢中提取到午餐需求: {food_req['has_lunch']}")
                break

        # 檢查晚餐需求
        for pattern in self.dinner_patterns:
            match = pattern.search(query)
            if match:
                # 檢查是否是否定表達
                matched_text = match.group(0)
                if "不" in matched_text or "沒" in matched_text:
                    food_req["has_dinner"] = False
                else:
                    food_req["has_dinner"] = True
                logger.debug(f"從查詢中提取到晚餐需求: {food_req['has_dinner']}")
                break

        return food_req
