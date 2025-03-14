"""
測試預算解析子Agent
"""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

import pytest

from src.agents.budget_parser_agent import BudgetParserAgent


@pytest.mark.asyncio
class TestBudgetParserAgent(IsolatedAsyncioTestCase):
    """測試預算解析子Agent"""

    def setUp(self):
        """設置測試環境"""
        self.agent = BudgetParserAgent()

    @patch("src.services.duckling_service.duckling_service.extract_budget")
    async def test_process_query(self, mock_extract_budget):
        """測試處理查詢中的預算範圍"""
        test_cases = [
            ("我想找2000-3000元的飯店", {"min": 2000, "max": 3000}),
            ("最高2000元的飯店", {"min": None, "max": 2000}),
            ("最低1500台幣的房間", {"min": 1500, "max": None}),
            ("2000元左右的飯店", {"min": 1600, "max": 2400}),
            ("預算3000元", {"min": 2400, "max": 3600}),
            ("我想找價格在2000到3000元之間的飯店", {"min": 2000, "max": 3000}),
            ("預算大約2000元", {"min": 1600, "max": 2400}),
            ("我的預算是最多3000元", {"min": None, "max": 3000}),
            ("至少要1500元的房間", {"min": 1500, "max": None}),
            ("我想要花費約2500元的住宿", {"min": 2000, "max": 3000}),
            ("價格在1000元以內的飯店", {"min": None, "max": 1000}),
            ("預算2000元以上的高級飯店", {"min": 2000, "max": None}),
            ("我想住便宜的飯店", {"min": None, "max": None}),
            ("有沒有舒適的住宿", {"min": None, "max": None}),
        ]

        for query, expected_budget in test_cases:
            with self.subTest(query=query):
                # 設置 mock 的返回值
                mock_extract_budget.return_value = expected_budget

                # 執行測試
                result = await self.agent._process_query(query, {})

                # 驗證 duckling_service.extract_budget 被正確調用
                mock_extract_budget.assert_called_with(query)

                # 驗證結果
                assert result["budget"] == expected_budget

    async def test_validate_budget(self):
        """測試驗證預算的有效性"""
        test_cases = [
            ({"min": 2000, "max": 1000}, {"min": 1000, "max": 2000}),  # 最低價格大於最高價格
            ({"min": -100, "max": 1000}, {"min": 0, "max": 1000}),  # 最低價格小於0
            ({"min": 1000, "max": -100}, {"min": 0, "max": 1000}),  # 最低價格大於最高價格且最高價格小於0
            ({"min": 1000, "max": 2000}, {"min": 1000, "max": 2000}),  # 正常情況
        ]

        for budget, expected in test_cases:
            with self.subTest(budget=budget):
                budget_copy = budget.copy()
                self.agent._validate_budget(budget_copy)
                assert budget_copy == expected

    @patch("src.services.duckling_service.duckling_service.extract_budget")
    async def test_chinese_number_range(self, mock_extract_budget):
        """測試中文數字範圍的處理"""
        test_cases = [
            {"query": "兩千三到五千", "expected": {"min": 2300, "max": 5000}},
            {"query": "一千五百到三千", "expected": {"min": 1500, "max": 3000}},
            {"query": "五百至一千二", "expected": {"min": 500, "max": 1200}},
            {"query": "兩千-四千五", "expected": {"min": 2000, "max": 4500}},
            {"query": "三千~六千", "expected": {"min": 3000, "max": 6000}},
            {"query": "預算在一千到兩千之間", "expected": {"min": 1000, "max": 2000}},
            {"query": "價格大約三千元", "expected": {"min": 2400, "max": 3600}},
            {"query": "最高五千元", "expected": {"min": None, "max": 5000}},
            {"query": "最低兩千元", "expected": {"min": 2000, "max": None}},
        ]

        for case in test_cases:
            with self.subTest(query=case["query"]):
                # 設置 mock 的返回值
                mock_extract_budget.return_value = case["expected"]

                # 執行測試
                result = await self.agent._process_query(case["query"], {})

                # 驗證 duckling_service.extract_budget 被正確調用
                mock_extract_budget.assert_called_with(case["query"])

                # 驗證結果
                assert result["budget"] == case["expected"]

    @patch("src.services.duckling_service.duckling_service.extract_budget")
    async def test_mixed_number_format(self, mock_extract_budget):
        """測試混合數字格式的處理"""
        test_cases = [
            {"query": "兩千到2500元", "expected": {"min": 2000, "max": 2500}},
            {"query": "1000到三千元", "expected": {"min": 1000, "max": 3000}},
            {"query": "預算1500到四千", "expected": {"min": 1500, "max": 4000}},
            {"query": "價格在800至一千二", "expected": {"min": 800, "max": 1200}},
        ]

        for case in test_cases:
            with self.subTest(query=case["query"]):
                # 設置 mock 的返回值
                mock_extract_budget.return_value = case["expected"]

                # 執行測試
                result = await self.agent._process_query(case["query"], {})

                # 驗證 duckling_service.extract_budget 被正確調用
                mock_extract_budget.assert_called_with(case["query"])

                # 驗證結果
                assert result["budget"] == case["expected"]

    @patch("src.services.duckling_service.duckling_service.extract_budget")
    async def test_process_query_with_duckling_failure(self, mock_extract_budget):
        """測試當 Duckling 服務失敗時的處理"""
        # 模擬 Duckling 服務失敗
        mock_extract_budget.side_effect = Exception("Duckling 服務連接失敗")

        # 測試案例
        query = "我想找2000-3000元的飯店"

        # 執行測試
        result = await self.agent._process_query(query, {})

        # 驗證結果 - 應該返回空預算
        assert result["budget"] == {"min": None, "max": None}
