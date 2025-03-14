"""
日期解析子Agent，專門負責解析查詢中的旅遊日期
"""

import re
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent
from src.services.duckling_service import duckling_service


class DateParserAgent(BaseSubAgent):
    """日期解析子Agent"""

    def __init__(self):
        """初始化日期解析子Agent"""
        super().__init__("DateParserAgent")
        # 日期正則表達式模式
        self.date_patterns = [
            # YYYY-MM-DD 或 YYYY/MM/DD
            re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"),
            # MM-DD 或 MM/DD
            re.compile(r"(\d{1,2})[/-](\d{1,2})"),
            # 中文日期格式：X月X日
            re.compile(r"(\d{1,2})月(\d{1,2})日"),
            # 中文日期格式：X月X號
            re.compile(r"(\d{1,2})月(\d{1,2})號"),
        ]

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的旅遊日期"""
        logger.info(f"解析查詢中的旅遊日期: {query}")

        # 使用 Duckling 服務提取日期
        try:
            dates = await duckling_service.extract_dates(query)

            # 如果 Duckling 無法解析，嘗試使用正則表達式解析日期
            if not dates.get("check_in") or not dates.get("check_out"):
                regex_dates = self._extract_dates_with_regex(query)

                # 合併結果，優先使用 Duckling 解析的結果
                if not dates.get("check_in") and regex_dates.get("check_in"):
                    dates["check_in"] = regex_dates["check_in"]

                if not dates.get("check_out") and regex_dates.get("check_out"):
                    dates["check_out"] = regex_dates["check_out"]

            # 如果仍然無法解析，嘗試根據上下文推斷
            if not dates.get("check_in") or not dates.get("check_out"):
                inferred_dates = self._infer_dates(query)

                # 合併結果，優先使用已解析的結果
                if not dates.get("check_in") and inferred_dates.get("check_in"):
                    dates["check_in"] = inferred_dates["check_in"]

                if not dates.get("check_out") and inferred_dates.get("check_out"):
                    dates["check_out"] = inferred_dates["check_out"]
        except Exception as e:
            logger.error(f"使用 Duckling 服務提取日期時發生錯誤: {e}")
            # 如果 Duckling 服務失敗，回退到正則表達式和推斷方法
            dates = self._extract_dates_with_regex(query)

            if not dates.get("check_in") or not dates.get("check_out"):
                inferred_dates = self._infer_dates(query)

                if not dates.get("check_in") and inferred_dates.get("check_in"):
                    dates["check_in"] = inferred_dates["check_in"]

                if not dates.get("check_out") and inferred_dates.get("check_out"):
                    dates["check_out"] = inferred_dates["check_out"]

        # 驗證日期的有效性
        self._validate_dates(dates)

        return {"dates": dates}

    def _extract_dates_with_regex(self, query: str) -> dict[str, str]:
        """使用正則表達式從查詢中提取日期"""
        dates = {"check_in": None, "check_out": None}

        # 提取所有可能的日期
        all_dates = []
        current_year = datetime.now().year

        for pattern in self.date_patterns:
            matches = pattern.findall(query)
            for match in matches:
                try:
                    if len(match) == 3:  # YYYY-MM-DD
                        year, month, day = int(match[0]), int(match[1]), int(match[2])
                        date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    elif len(match) == 2:  # MM-DD 或 中文日期
                        month, day = int(match[0]), int(match[1])
                        date_str = f"{current_year:04d}-{month:02d}-{day:02d}"

                    # 驗證日期有效性
                    datetime.strptime(date_str, "%Y-%m-%d%z")
                    all_dates.append(date_str)
                except (ValueError, IndexError):
                    continue

        # 如果找到至少兩個日期，假設第一個是入住日期，第二個是退房日期
        if len(all_dates) >= 2:
            # 排序日期，確保入住日期在前
            all_dates.sort()
            dates["check_in"] = all_dates[0]
            dates["check_out"] = all_dates[1]
        elif len(all_dates) == 1:
            # 如果只找到一個日期，假設是入住日期，退房日期為入住日期後的第二天
            dates["check_in"] = all_dates[0]
            check_in_date = datetime.strptime(all_dates[0], "%Y-%m-%d%z")
            check_out_date = check_in_date + timedelta(days=1)
            dates["check_out"] = check_out_date.strftime("%Y-%m-%d")

        return dates

    def _infer_dates(self, query: str) -> dict[str, str]:
        """根據查詢內容推斷日期"""
        dates = {"check_in": None, "check_out": None}
        today = datetime.now()

        # 檢查是否包含特定關鍵詞
        if "今天" in query or "今晚" in query:
            dates["check_in"] = today.strftime("%Y-%m-%d")
            dates["check_out"] = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "明天" in query:
            tomorrow = today + timedelta(days=1)
            dates["check_in"] = tomorrow.strftime("%Y-%m-%d")
            dates["check_out"] = (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "後天" in query:
            day_after_tomorrow = today + timedelta(days=2)
            dates["check_in"] = day_after_tomorrow.strftime("%Y-%m-%d")
            dates["check_out"] = (day_after_tomorrow + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "這週末" in query or "這個週末" in query:
            # 計算到本週六的天數
            days_until_saturday = (5 - today.weekday()) % 7
            saturday = today if days_until_saturday == 0 else today + timedelta(days=days_until_saturday)
            sunday = saturday + timedelta(days=1)

            dates["check_in"] = saturday.strftime("%Y-%m-%d")
            dates["check_out"] = sunday.strftime("%Y-%m-%d")
        elif "下週" in query or "下個週" in query:
            # 計算到下週一的天數
            days_until_next_monday = (7 - today.weekday()) % 7
            if days_until_next_monday == 0:  # 如果今天是週一
                days_until_next_monday = 7

            next_monday = today + timedelta(days=days_until_next_monday)
            next_wednesday = next_monday + timedelta(days=2)

            dates["check_in"] = next_monday.strftime("%Y-%m-%d")
            dates["check_out"] = next_wednesday.strftime("%Y-%m-%d")

        return dates

    def _validate_dates(self, dates: dict[str, str]) -> None:
        """驗證日期的有效性"""
        today = datetime.now().date()

        # 檢查入住日期
        if dates.get("check_in"):
            try:
                check_in_date = datetime.strptime(dates["check_in"], "%Y-%m-%d%z").date()

                # 入住日期不能早於今天
                if check_in_date < today:
                    logger.warning(f"入住日期 {dates['check_in']} 早於今天，設置為今天")
                    dates["check_in"] = today.strftime("%Y-%m-%d")
            except ValueError:
                logger.error(f"無效的入住日期格式: {dates['check_in']}")
                dates["check_in"] = None

        # 檢查退房日期
        if dates.get("check_out"):
            try:
                check_out_date = datetime.strptime(dates["check_out"], "%Y-%m-%d%z").date()

                # 如果有入住日期，退房日期必須晚於入住日期
                if dates.get("check_in"):
                    check_in_date = datetime.strptime(dates["check_in"], "%Y-%m-%d%z").date()
                    if check_out_date <= check_in_date:
                        logger.warning(
                            f"退房日期 {dates['check_out']} 不晚於入住日期 {dates['check_in']}，設置為入住日期後一天"
                        )
                        dates["check_out"] = (check_in_date + timedelta(days=1)).strftime("%Y-%m-%d")
            except ValueError:
                logger.error(f"無效的退房日期格式: {dates['check_out']}")
                dates["check_out"] = None


# 創建日期解析子Agent實例
date_parser_agent = DateParserAgent()
