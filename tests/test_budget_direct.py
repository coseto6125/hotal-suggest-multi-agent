"""
直接測試 BudgetParserAgent 的腳本，不通過導入
"""

import re
from typing import Any

from src.agents.base.base_agent import BaseAgent


class BudgetParserAgentTest(BaseAgent):
    """預算解析子Agent測試類"""

    def __init__(self):
        """初始化預算解析子Agent"""
        super().__init__("BudgetParserAgentTest")
        # 預算正則表達式模式
        self.price_range_patterns = [
            # 範圍格式：X-Y元/塊/NT$/台幣
            re.compile(
                r"(\d+(?:,\d+)?)\s*(?:-|~|到)\s*(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)?(?:/晚|每晚|一晚)?"
            ),
        ]

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        處理標準化後的輸入，實現 BaseAgent 的抽象方法
        """
        return {"test": "success"}


try:
    print("正在嘗試實例化 BudgetParserAgentTest...")
    budget_parser = BudgetParserAgentTest()

    print(f"budget_parser 類型: {type(budget_parser)}")
    print("BudgetParserAgentTest 實例化成功!")
except Exception as e:
    print(f"發生錯誤: {e}")
