"""
Duckling 服務模組，用於處理結構化數據解析
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import aiohttp
import docker
from docker.errors import DockerException, NotFound
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
        self.container_name = "duckling-server"
        self._initialized = False

    async def initialize(self) -> None:
        """異步初始化服務"""
        if self._initialized:
            return
        await self._ensure_duckling_running()
        self._initialized = True

    def _wait_for_docker(self, max_retries: int = 5, delay: float = 2.0) -> docker.DockerClient | None:
        """
        等待 Docker 服務啟動

        Args:
            max_retries: 最大重試次數
            delay: 每次重試間隔（秒）

        Returns:
            docker.DockerClient | None: Docker 客戶端實例，如果無法連接則返回 None
        """
        for attempt in range(max_retries):
            try:
                client = docker.from_env()
                client.ping()
                return client
            except DockerException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"等待 Docker 服務啟動 (嘗試 {attempt + 1}/{max_retries}): {e}")
                    if "系統找不到指定的檔案" in str(e):
                        logger.error("""
Docker 服務未啟動或未安裝，請確認：
1. Docker Desktop 是否已安裝？
   - 如果未安裝，請從 https://www.docker.com/products/docker-desktop 下載並安裝
2. Docker Desktop 是否已啟動？
   - 請在系統匣找到 Docker Desktop 圖示並啟動
3. 安裝完成後是否已重新啟動電腦？
   - 建議重新啟動電腦以確保 Docker 服務正確啟動
""")
                    time.sleep(delay)
                else:
                    logger.error(f"無法連接到 Docker 服務: {e}")
                    return None
        return None

    async def _ensure_duckling_running(self) -> None:
        """確保 Duckling Docker 容器正在運行"""
        try:
            # 等待 Docker 服務啟動
            client = self._wait_for_docker()
            if client is None:
                logger.error("無法啟動 Duckling 服務：Docker 服務未就緒")
                return

            # 檢查容器是否存在
            try:
                container = client.containers.get(self.container_name)
                if container.status != "running":
                    logger.info(f"Duckling 容器狀態為 {container.status}，正在啟動...")
                    container.start()
            except NotFound:
                logger.info("Duckling 容器不存在，正在創建...")
                try:
                    client.images.get("rasa/duckling")
                except docker.errors.ImageNotFound:
                    logger.info("正在下載 Duckling 映像檔...")
                    client.images.pull("rasa/duckling")

                client.containers.run("rasa/duckling", name=self.container_name, ports={"8000/tcp": 6579}, detach=True)

            # 等待服務啟動
            await self._wait_for_service()
            logger.info("Duckling 服務已成功啟動")

        except Exception as e:
            logger.error(f"啟動 Duckling 服務時發生錯誤: {e}")

    async def _wait_for_service(self, max_retries: int = 30, delay: float = 1.0) -> None:
        """
        等待 Duckling 服務啟動

        Args:
            max_retries: 最大重試次數
            delay: 每次重試間隔（秒）
        """
        async with aiohttp.ClientSession() as session:
            for _ in range(max_retries):
                try:
                    async with session.post(
                        f"{self.base_url}/parse",
                        data={"locale": self.locale, "text": "test"},
                        timeout=aiohttp.ClientTimeout(total=2),
                    ) as response:
                        if response.status == 200:
                            return
                except Exception:
                    pass
                await asyncio.sleep(delay)

        logger.warning("Duckling 服務啟動超時")

    async def _ensure_session(self):
        """確保 aiohttp 會話已創建且 Duckling 服務已初始化"""
        if not self._initialized:
            await self.initialize()
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
        dcm = lambda x: Decimal(str(x))

        # 先嘗試解析數字，因為對中文數字的支援較好
        results = await self.parse(text, dimensions=["number"])
        results += await self.parse(text, dimensions=["amount-of-money"])
        results = results[::-1]

        if not results:
            return budget

        def extract_amount(val: str) -> int:
            """處理數字，特別是中文數字的轉換"""
            if isinstance(val, int):
                return val

            base = int(val)  # 基數部分，例如 2000.3 中的 2000
            decimal = dcm(val) - dcm(base)  # 小數部分，例如 2000.3 中的 0.3

            # 處理類似 "兩千三" 這樣的中文數字
            if 0.1 <= decimal <= 0.9:
                # 獲取小數部分的第一位數字
                decimal_digit = int(dcm(decimal) * dcm(10))

                # 根據基數的大小來決定單位
                if base >= 10000:  # 萬位
                    return base + decimal_digit * 1000  # 一萬二 -> 12000
                if base >= 1000:  # 千位
                    return base + decimal_digit * 100  # 兩千三 -> 2300
                if base >= 100:  # 百位
                    return base + decimal_digit * 10  # 三百四 -> 340

            return base

        # 處理解析結果
        amounts = []
        for result in results:
            if result.get("dim") == "amount-of-money" or result.get("dim") == "number":
                value = result.get("value", {})

                # 處理區間格式
                if value.get("type") == "interval":
                    from_value = value.get("from", {}).get("value")
                    to_value = value.get("to", {}).get("value")
                    if from_value is not None:
                        amounts.append(extract_amount(from_value))
                    if to_value is not None:
                        amounts.append(extract_amount(to_value))
                    if len(amounts) >= 2:
                        budget["min"] = int(min(amounts))
                        budget["max"] = int(max(amounts))
                        return budget
                    budget["min"] = int(min(amounts))
                    return budget

                # 處理單一值
                if value.get("value") is not None:
                    val = value["value"]
                    amounts.append(extract_amount(val))

        # 處理負數（可能是由於 Duckling 誤解 "-" 為負號）
        amounts = [abs(x) for x in amounts]

        # 合併相鄰的數字（例如：兩千三）
        if len(amounts) >= 2:
            merged_amounts = []
            i = 0
            while i < len(amounts):
                if i + 1 < len(amounts):
                    curr = amounts[i]
                    next_val = amounts[i + 1]

                    # 如果當前數字是千位，且下一個數字小於 1000
                    if curr >= 1000 and next_val < 1000 and next_val % 100 == 0:
                        merged_amounts.append(curr + (next_val // 100) * 100)
                        i += 2
                        continue
                merged_amounts.append(amounts[i])
                i += 1
            amounts = merged_amounts

        # 檢查價格限制關鍵詞
        min_price_keywords = ["最低", "至少", "起", "以上"]
        max_price_keywords = ["最高", "最多", "以下", "以內", "內", "不超過"]

        has_min_keyword = any(keyword in text for keyword in min_price_keywords)
        has_max_keyword = any(keyword in text for keyword in max_price_keywords)

        # 檢查範圍關鍵詞
        range_keywords = ["到", "至", "-", "~", "左右", "上下"]
        has_range = any(keyword in text for keyword in range_keywords)

        # 根據找到的金額和關鍵詞設置預算範圍
        if amounts:
            if len(amounts) == 1:
                amount = amounts[0]
                if has_min_keyword and not has_max_keyword:
                    budget["min"] = amount
                elif has_max_keyword and not has_min_keyword:
                    budget["max"] = amount
                elif has_range:
                    # 如果有範圍關鍵詞，設置一個合理的範圍
                    budget["min"] = int(amount * 0.8)
                    budget["max"] = int(amount * 1.2)
                else:
                    budget["min"] = amount
                    budget["max"] = amount
            else:
                budget["min"] = min(amounts)
                budget["max"] = max(amounts)

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
