"""
預算解析子Agent，專門負責解析查詢中的預算範圍
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent


class BudgetParserAgent(BaseAgent):
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

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        處理預算解析請求
        """
        logger.debug(f"[{self.name}] 開始處理預算解析請求")

        # 從輸入中提取查詢和上下文
        query = state.get("query", "")
        context = state.get("context", {})

        try:
            if not query:
                # 如果沒有查詢文本，嘗試從上下文或其他字段獲取信息
                if "budget" in context:
                    return {
                        "lowest_price": context["budget"].get("min", 0),
                        "highest_price": context["budget"].get("max", 0),
                    }

                logger.warning(f"[{self.name}] 沒有有效的查詢文本和預算上下文")
                return {}

            # 使用正則表達式提取預算信息
            budget_info = self._extract_budget_with_regex(query)

            # 檢查是否成功提取到預算
            if not budget_info or not (budget_info.get("lowest_price") or budget_info.get("highest_price")):
                # 如果沒有提取到預算，返回空結果
                logger.info(f"[{self.name}] 未從查詢 '{query}' 中提取到預算信息")
                return {}

            # 驗證預算範圍 - 不再自動填充缺失的價格
            self._validate_budget_range(budget_info)

            logger.info(f"[{self.name}] 成功從查詢 '{query}' 中提取預算信息: {budget_info}")
            return budget_info

        except Exception as e:
            logger.error(f"[{self.name}] 預算解析出錯: {e}")
            return {}

    def _extract_budget_with_regex(self, query: str) -> dict[str, Any]:
        """使用正則表達式從查詢中提取預算"""
        result = {}

        # 檢查是否是範圍預算
        for pattern in self.price_range_patterns:
            match = pattern.search(query)
            if match:
                groups = match.groups()

                # 處理不同類型的匹配
                if len(groups) == 2 and groups[0] and groups[1]:  # 範圍格式：X-Y元
                    # 移除千分位逗號
                    min_str = groups[0].replace(",", "")
                    max_str = groups[1].replace(",", "")

                    try:
                        min_amount = int(float(min_str))
                        max_amount = int(float(max_str))

                        # 檢查是否為萬元單位
                        if "萬" in query:
                            min_amount *= 10000
                            max_amount *= 10000

                        # 檢查是否為千元單位
                        if "k" in query.lower() or "千" in query:
                            min_amount *= 1000
                            max_amount *= 1000

                        return {"lowest_price": min_amount, "highest_price": max_amount}
                    except ValueError:
                        continue

                elif len(groups) == 1 and groups[0]:  # 單一價格格式
                    # 移除千分位逗號
                    amount_str = groups[0].replace(",", "")

                    try:
                        amount = int(float(amount_str))

                        # 檢查是否為萬元單位
                        if "萬" in query:
                            amount *= 10000

                        # 檢查是否為千元單位
                        if "k" in query.lower() or "千" in query:
                            amount *= 1000

                        # 檢查是否包含特定詞彙，判斷是最低還是最高價格
                        if "最低" in match.string or "至少" in match.string or "起碼" in match.string:
                            return {
                                "lowest_price": amount,
                                "highest_price": amount * 2,  # 估計最高價格為最低價格的兩倍
                            }
                        if "最高" in match.string or "最多" in match.string or "不超過" in match.string:
                            return {
                                "lowest_price": int(amount * 0.5),  # 估計最低價格為最高價格的一半
                                "highest_price": amount,
                            }
                        # 一般價格，加減20%作為範圍
                        buffer = int(amount * 0.2)
                        return {"lowest_price": max(0, amount - buffer), "highest_price": amount + buffer}
                    except ValueError:
                        continue

        # 預算金額正則表達式模式（後備方案）
        amount_pattern = r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:萬|k|K|千|元|塊|NTD|TWD|台幣|新台幣)?"
        amount_match = re.search(amount_pattern, query)

        if amount_match:
            # 提取金額
            amount_str = amount_match.group(1).replace(",", "")
            try:
                amount = float(amount_str)

                # 檢查是否為萬元單位
                if "萬" in query:
                    amount *= 10000

                # 檢查是否為千元單位
                if "k" in query.lower() or "千" in query:
                    amount *= 1000

                amount = int(amount)
                buffer = int(amount * 0.2)

                return {"lowest_price": max(0, amount - buffer), "highest_price": amount + buffer}
            except ValueError:
                pass

        # 如果沒有找到匹配的模式，返回空結果
        return result

    def _validate_budget_range(self, budget: dict[str, Any]) -> None:
        """驗證預算範圍的有效性"""
        lowest = budget.get("lowest_price")
        highest = budget.get("highest_price")

        # 如果最低價格大於最高價格，交換它們
        if lowest is not None and highest is not None and lowest > highest:
            logger.warning(f"最低價格 {lowest} 大於最高價格 {highest}，交換它們")
            budget["lowest_price"], budget["highest_price"] = highest, lowest

        # 如果最低價格小於0，設置為0
        if lowest is not None and lowest < 0:
            logger.warning(f"最低價格 {lowest} 小於0，設置為0")
            budget["lowest_price"] = 0

        # 如果最高價格小於0，移除該欄位
        if highest is not None and highest < 0:
            logger.warning(f"最高價格 {highest} 小於0，移除該欄位")
            budget.pop("highest_price", None)
