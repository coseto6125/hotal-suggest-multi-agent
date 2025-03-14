"""
API 客戶端，用於與外部API進行通信
"""

import aiohttp
import orjson
from loguru import logger

from src.config import config


class APIClient:
    """API 客戶端"""

    def __init__(self):
        self.base_url = config.api.base_url
        self.api_key = config.api.api_key
        self.timeout = config.api.timeout
        self.headers = {"Authorization": self.api_key, "Content-Type": "application/json"}

    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        """發送GET請求"""
        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    return await response.json(loads=orjson.loads)
        except aiohttp.ClientError as e:
            logger.error(f"API請求失敗: {url}, 錯誤: {e!s}")
            raise

    async def post(self, endpoint: str, data: dict) -> dict:
        """發送POST請求"""
        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=data, headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    return await response.json(loads=orjson.loads)
        except aiohttp.ClientError as e:
            logger.error(f"API請求失敗: {url}, 錯誤: {e!s}")
            raise


# 創建API客戶端實例
api_client = APIClient()
