"""
測試日期解析功能
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from loguru import logger

from src.agents.parsers.date_parser_agent import DateParserAgent


@pytest.mark.asyncio
async def test_date_parser():
    """測試日期解析功能"""
    # 初始化日期解析器
    date_parser = DateParserAgent()

    # 測試用例
    test_cases = [
        # 標準日期格式
        {
            "query": "我想在2023-05-15入住，2023-05-17退房",
            "expected": {"check_in": "2023-05-15", "check_out": "2023-05-17"},
        },
        {
            "query": "我想在5月15日入住，5月17日退房",
            "expected": {"check_in": f"{datetime.now().year}-05-15", "check_out": f"{datetime.now().year}-05-17"},
        },
        {
            "query": "我想在5/15入住，5/17退房",
            "expected": {"check_in": f"{datetime.now().year}-05-15", "check_out": f"{datetime.now().year}-05-17"},
        },
        # 日期範圍表達
        {
            "query": "我想在5月15日至5月17日入住",
            "expected": {"check_in": f"{datetime.now().year}-05-15", "check_out": f"{datetime.now().year}-05-17"},
        },
        {
            "query": "我想在5月15日至17日入住",
            "expected": {"check_in": f"{datetime.now().year}-05-15", "check_out": f"{datetime.now().year}-05-17"},
        },
        # 相對日期表達
        {
            "query": "我想今天入住，明天退房",
            "expected": {
                "check_in": datetime.now().strftime("%Y-%m-%d"),
                "check_out": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            },
        },
        {
            "query": "我想明天入住，後天退房",
            "expected": {
                "check_in": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "check_out": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
            },
        },
        {"query": "我想這週末入住", "expected": None},  # 這個需要根據當前日期動態計算
        # 混合表達
        {
            "query": "我想在台北市5月15日入住一晚",
            "expected": {"check_in": f"{datetime.now().year}-05-15", "check_out": f"{datetime.now().year}-05-16"},
        },
        {
            "query": "我想帶2大1小去台北市5月15日至17日玩",
            "expected": {"check_in": f"{datetime.now().year}-05-15", "check_out": f"{datetime.now().year}-05-17"},
        },
        # 特殊表達
        {"query": "我想下週一入住，下週三退房", "expected": None},  # 這個需要根據當前日期動態計算
        {"query": "我想下個月1號入住，3號退房", "expected": None},  # 這個需要特殊處理
    ]

    # 執行測試
    for i, test_case in enumerate(test_cases):
        logger.info(f"測試用例 {i + 1}: {test_case['query']}")

        # 使用日期解析器處理查詢
        result = await date_parser.process({"query": test_case["query"]})

        # 輸出結果
        if "error" in result:
            logger.warning(f"解析失敗: {result['error']}")
            continue

        logger.info(f"解析結果: 入住 {result.get('check_in', '未知')}，退房 {result.get('check_out', '未知')}")

        # 驗證結果
        if test_case["expected"] is not None:
            check_in_match = result.get("check_in") == test_case["expected"]["check_in"]
            check_out_match = result.get("check_out") == test_case["expected"]["check_out"]

            if check_in_match and check_out_match:
                logger.success("測試通過 ✓")
            else:
                logger.error(f"測試失敗 ✗ - 預期: {test_case['expected']}, 實際: {result}")
        else:
            logger.info("此測試用例需要手動驗證")

    # 測試 spaCy 特定功能
    if date_parser.spacy_available:
        logger.info("測試 spaCy 特定功能")

        spacy_test_cases = [
            {"query": "我想在五月十五日入住，五月十七日退房", "expected": None},  # 中文數字日期
            {"query": "我想在下週末入住兩晚", "expected": None},  # 週末表達
            {"query": "我想在下週一入住，下週三退房", "expected": None},  # 下週X
        ]

        for i, test_case in enumerate(spacy_test_cases):
            logger.info(f"spaCy 測試用例 {i + 1}: {test_case['query']}")

            # 使用日期解析器處理查詢
            result = await date_parser.process({"query": test_case["query"]})

            # 輸出結果
            if "error" in result:
                logger.warning(f"解析失敗: {result['error']}")
                continue

            logger.info(f"解析結果: 入住 {result.get('check_in', '未知')}，退房 {result.get('check_out', '未知')}")
            logger.info("此測試用例需要手動驗證")
    else:
        logger.warning("spaCy 不可用，跳過 spaCy 特定功能測試")


if __name__ == "__main__":
    # 設置日誌級別
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")

    # 運行測試
    asyncio.run(test_date_parser())
