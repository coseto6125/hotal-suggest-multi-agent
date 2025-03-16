"""
測試日期解析子Agent的功能
"""

import asyncio
import unittest
from datetime import datetime, timedelta

import pytest

from src.agents.date_parser_agent import DateParserAgent


@pytest.mark.asyncio
class TestDateParserAgent(unittest.TestCase):
    """測試日期解析子Agent"""

    def setUp(self):
        """設置測試環境"""
        self.agent = DateParserAgent()
        self.loop = asyncio.get_event_loop()
        # 計算未來的日期，用於測試
        self.future_date1 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        self.future_date2 = (datetime.now() + timedelta(days=33)).strftime("%Y-%m-%d")
        # 提取年、月、日
        self.future_year = self.future_date1[:4]
        self.future_month = self.future_date1[5:7]
        self.future_day1 = self.future_date1[8:10]
        self.future_day2 = self.future_date2[8:10]

    def test_extract_dates_with_regex_standard_format(self):
        """測試使用正則表達式解析標準格式日期"""
        # 測試不同的標準日期格式
        test_cases = [
            f"我想在{self.future_date1}入住，{self.future_date2}退房",
            f"預訂{self.future_year}/{self.future_month}/{self.future_day1}到{self.future_year}/{self.future_month}/{self.future_day2}的房間",
            f"{self.future_month}-{self.future_day1}到{self.future_month}-{self.future_day2}想要訂房",
            f"{self.future_month}/{self.future_day1}到{self.future_month}/{self.future_day2}想要訂房",
        ]

        current_year = datetime.now().year

        for query in test_cases:
            with self.subTest(query=query):
                result = self.agent._extract_dates_with_regex(query)
                if self.future_year in query:
                    self.assertEqual(result["check_in"], self.future_date1)
                    self.assertEqual(result["check_out"], self.future_date2)
                else:
                    expected_check_in = f"{current_year}-{self.future_month}-{self.future_day1}"
                    expected_check_out = f"{current_year}-{self.future_month}-{self.future_day2}"
                    self.assertEqual(result["check_in"], expected_check_in)
                    self.assertEqual(result["check_out"], expected_check_out)

    def test_extract_dates_with_regex_chinese_format(self):
        """測試使用正則表達式解析中文格式日期"""
        # 測試不同的中文日期格式
        test_cases = [
            f"我想在{self.future_month}月{self.future_day1}日入住，{self.future_month}月{self.future_day2}日退房",
            f"預訂{self.future_month}月{self.future_day1}號到{self.future_month}月{self.future_day2}號的房間",
        ]

        current_year = datetime.now().year

        for query in test_cases:
            with self.subTest(query=query):
                result = self.agent._extract_dates_with_regex(query)
                expected_check_in = f"{current_year}-{self.future_month}-{self.future_day1}"
                expected_check_out = f"{current_year}-{self.future_month}-{self.future_day2}"
                self.assertEqual(result["check_in"], expected_check_in)
                self.assertEqual(result["check_out"], expected_check_out)

    def test_extract_dates_with_regex_single_date(self):
        """測試使用正則表達式解析只有一個日期的查詢"""
        # 測試只有一個日期的情況
        test_cases = [f"我想在{self.future_date1}入住", f"預訂{self.future_month}月{self.future_day1}日的房間"]

        for query in test_cases:
            with self.subTest(query=query):
                result = self.agent._extract_dates_with_regex(query)
                if self.future_year in query:
                    self.assertEqual(result["check_in"], self.future_date1)
                    # 退房日期應該是入住日期的下一天
                    next_day = (datetime.strptime(self.future_date1, "%Y-%m-%d") + timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    )
                    self.assertEqual(result["check_out"], next_day)
                else:
                    current_year = datetime.now().year
                    expected_check_in = f"{current_year}-{self.future_month}-{self.future_day1}"
                    expected_check_out = (
                        datetime.strptime(expected_check_in, "%Y-%m-%d") + timedelta(days=1)
                    ).strftime("%Y-%m-%d")
                    self.assertEqual(result["check_in"], expected_check_in)
                    self.assertEqual(result["check_out"], expected_check_out)

    def test_infer_dates(self):
        """測試根據關鍵詞推斷日期"""
        # 測試不同的關鍵詞
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        test_cases = {
            "我想今天入住": {
                "check_in": today.strftime("%Y-%m-%d"),
                "check_out": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            },
            "明天有空房嗎": {
                "check_in": tomorrow.strftime("%Y-%m-%d"),
                "check_out": (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d"),
            },
            "後天想訂房": {
                "check_in": day_after_tomorrow.strftime("%Y-%m-%d"),
                "check_out": (day_after_tomorrow + timedelta(days=1)).strftime("%Y-%m-%d"),
            },
        }

        for query, expected in test_cases.items():
            with self.subTest(query=query):
                result = self.agent._infer_dates(query)
                self.assertEqual(result["check_in"], expected["check_in"])
                self.assertEqual(result["check_out"], expected["check_out"])

    def test_validate_dates(self):
        """測試日期驗證功能"""
        # 測試日期驗證
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # 測試入住日期早於今天的情況
        dates = {"check_in": yesterday.strftime("%Y-%m-%d"), "check_out": tomorrow.strftime("%Y-%m-%d")}
        self.agent._validate_dates(dates)
        self.assertEqual(dates["check_in"], today.strftime("%Y-%m-%d"))

        # 測試退房日期不晚於入住日期的情況
        dates = {"check_in": tomorrow.strftime("%Y-%m-%d"), "check_out": tomorrow.strftime("%Y-%m-%d")}
        self.agent._validate_dates(dates)
        self.assertEqual(dates["check_out"], (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d"))

    async def _async_test_extract_dates_with_llm(self):
        """測試使用LLM解析日期（異步測試輔助方法）"""
        # 測試使用LLM解析日期
        test_cases = ["我想下週入住", "這個週末有空房嗎", "下個月初想訂房"]

        for query in test_cases:
            result = await self.agent._extract_dates_with_llm(query)
            # 由於LLM結果可能會變化，我們只檢查返回格式是否正確
            self.assertIn("check_in", result)
            self.assertIn("check_out", result)

            # 如果有返回日期，檢查格式是否正確
            if result["check_in"]:
                datetime.strptime(result["check_in"], "%Y-%m-%d")
            if result["check_out"]:
                datetime.strptime(result["check_out"], "%Y-%m-%d")

    def test_extract_dates_with_llm(self):
        """測試使用LLM解析日期（同步包裝）"""
        # 跳過此測試，因為它需要實際調用LLM服務
        self.skipTest("此測試需要實際調用LLM服務，跳過")
        # 如果需要運行，取消下面的註釋
        # self.loop.run_until_complete(self._async_test_extract_dates_with_llm())

    async def _async_test_process(self):
        """測試處理查詢（異步測試輔助方法）"""
        # 測試完整的查詢處理流程
        test_cases = [f"我想在{self.future_date1}入住，{self.future_date2}退房", "明天有空房嗎", "下週想訂房"]

        for query in test_cases:
            result = await self.agent._process(query, {})
            self.assertIn("dates", result)
            dates = result["dates"]
            self.assertIn("check_in", dates)
            self.assertIn("check_out", dates)

            # 檢查日期格式是否正確
            if dates["check_in"]:
                datetime.strptime(dates["check_in"], "%Y-%m-%d")
            if dates["check_out"]:
                datetime.strptime(dates["check_out"], "%Y-%m-%d")

    def test_process(self):
        """測試處理查詢（同步包裝）"""
        # 跳過此測試，因為它可能需要調用LLM服務
        self.skipTest("此測試可能需要調用LLM服務，跳過")
        # 如果需要運行，取消下面的註釋
        # self.loop.run_until_complete(self._async_test_process())

    def test_integration(self):
        """集成測試：測試各種日期表達方式的解析"""
        # 測試各種日期表達方式
        test_cases = [
            {
                "query": f"我想在{self.future_date1}入住，{self.future_date2}退房",
                "expected": {"check_in": self.future_date1, "check_out": self.future_date2},
            },
            {
                "query": f"{self.future_month}月{self.future_day1}日到{self.future_month}月{self.future_day2}日",
                "expected": {
                    "check_in": f"{datetime.now().year}-{self.future_month}-{self.future_day1}",
                    "check_out": f"{datetime.now().year}-{self.future_month}-{self.future_day2}",
                },
            },
            {
                "query": "今天入住",
                "expected": {
                    "check_in": datetime.now().strftime("%Y-%m-%d"),
                    "check_out": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                },
            },
            {
                "query": "明天有空房嗎",
                "expected": {
                    "check_in": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "check_out": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
                },
            },
        ]

        for test_case in test_cases:
            query = test_case["query"]
            expected = test_case["expected"]

            with self.subTest(query=query):
                # 首先嘗試使用正則表達式解析
                result = self.agent._extract_dates_with_regex(query)

                # 如果正則表達式無法解析，嘗試使用推斷
                if not result["check_in"] or not result["check_out"]:
                    inferred = self.agent._infer_dates(query)
                    if not result["check_in"] and inferred["check_in"]:
                        result["check_in"] = inferred["check_in"]
                    if not result["check_out"] and inferred["check_out"]:
                        result["check_out"] = inferred["check_out"]

                # 驗證日期
                self.agent._validate_dates(result)

                # 檢查結果是否符合預期
                self.assertEqual(result["check_in"], expected["check_in"])
                self.assertEqual(result["check_out"], expected["check_out"])


if __name__ == "__main__":
    unittest.main()
