"""
Duckling 服務模組，用於處理結構化數據解析
"""

import json
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from loguru import logger

from src.config import config


class DucklingService:
    """Facebook Duckling 服務包裝器"""

    def __init__(self):
        """初始化 Duckling 服務"""
        self.base_url = config.duckling.base_url
        self.timeout = config.duckling.timeout
        self.locale = config.duckling.locale
        self.dimensions = ["amount-of-money", "number", "quantity"]
        self.session = None

    async def _ensure_session(self):
        """確保 aiohttp 會話已創建"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))

    async def close(self):
        """關閉 aiohttp 會話"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def parse(
        self, text: str, dimensions: list[str] | None = None, locale: str | None = None
    ) -> list[dict[str, Any]]:
        """
        解析文本中的結構化數據

        Args:
            text: 要解析的文本
            dimensions: 要解析的維度，默認為 ["amount-of-money", "number", "quantity"]
            locale: 語言區域，默認為 zh_TW

        Returns:
            解析結果列表
        """
        await self._ensure_session()

        if dimensions is None:
            dimensions = self.dimensions

        if locale is None:
            locale = self.locale

        try:
            payload = {"locale": locale, "text": text, "dims": json.dumps(dimensions)}

            async with self.session.post(f"{self.base_url}/parse", data=payload) as response:
                if response.status != 200:
                    logger.error(f"Duckling 服務請求失敗: {response.status}")
                    return []

                result = await response.json()
                return result
        except Exception as e:
            logger.error(f"Duckling 服務請求異常: {e}")
            return []

    async def extract_budget(self, text: str) -> dict[str, int | None]:
        """
        從文本中提取預算信息

        Args:
            text: 要解析的文本

        Returns:
            包含最小和最大預算的字典 {"min": min_value, "max": max_value}
        """
        budget = {"min": None, "max": None}

        # 解析金額
        results = await self.parse(text, dimensions=["amount-of-money"])

        if not results:
            # 如果沒有找到金額，嘗試解析數字
            results = await self.parse(text, dimensions=["number"])

        if not results:
            return budget

        # 處理解析結果
        amounts = []
        for result in results:
            if result.get("dim") == "amount-of-money" or result.get("dim") == "number":
                value = result.get("value", {}).get("value")
                if value is not None:
                    amounts.append(value)

        # 根據找到的金額設置預算範圍
        if len(amounts) == 1:
            # 單一金額，設置為最大值
            budget["max"] = int(amounts[0])
        elif len(amounts) >= 2:
            # 多個金額，取最小和最大值
            budget["min"] = int(min(amounts))
            budget["max"] = int(max(amounts))

        return budget

    async def extract_dates(self, text: str) -> dict[str, str | None]:
        """
        從文本中提取日期信息

        Args:
            text: 要解析的文本

        Returns:
            包含入住和退房日期的字典 {"check_in": check_in_date, "check_out": check_out_date}
        """
        dates = {"check_in": None, "check_out": None}

        # 解析日期
        results = await self.parse(text, dimensions=["time"])

        if not results:
            return dates

        # 處理解析結果
        all_dates = []
        for result in results:
            if result.get("dim") == "time":
                value = result.get("value", {})

                # 優先使用 value.value，這通常是標準化的日期時間
                if "value" in value:
                    date_str = value["value"].split("T")[0]  # 只取日期部分
                    all_dates.append(date_str)
                # 如果沒有 value.value，嘗試使用 value.from
                elif "from" in value:
                    date_str = value["from"].get("value", "").split("T")[0]
                    if date_str:
                        all_dates.append(date_str)
                # 如果有 value.to，也加入
                if "to" in value:
                    date_str = value["to"].get("value", "").split("T")[0]
                    if date_str:
                        all_dates.append(date_str)

        # 根據找到的日期設置入住和退房日期
        if all_dates:
            # 去除重複日期並排序
            unique_dates = sorted(list(set(all_dates)))

            if len(unique_dates) >= 2:
                # 如果找到至少兩個日期，假設第一個是入住日期，第二個是退房日期
                dates["check_in"] = unique_dates[0]
                dates["check_out"] = unique_dates[1]
            elif len(unique_dates) == 1:
                # 如果只找到一個日期，假設是入住日期，退房日期為入住日期後的第二天
                dates["check_in"] = unique_dates[0]
                check_in_date = datetime.strptime(unique_dates[0], "%Y-%m-%d")
                check_out_date = check_in_date + timedelta(days=1)
                dates["check_out"] = check_out_date.strftime("%Y-%m-%d")

        return dates


# 創建 Duckling 服務實例
duckling_service = DucklingService()
