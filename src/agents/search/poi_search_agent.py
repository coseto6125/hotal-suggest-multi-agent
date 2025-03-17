"""
周邊地標搜索 Agent 模塊
負責搜索旅館附近的地標，如景點、餐廳和交通設施。
"""

import asyncio
from typing import Any

import aiohttp
from loguru import logger

from src.agents.base.base_agent import BaseAgent

# 假設你的 POI API endpoint 為此（請根據實際情況修改）
BASE_POI_API_URL = "https://api.example.com/places/nearby"


class POISearchAgent(BaseAgent):
    """周邊地標搜索 Agent"""

    def __init__(self):
        """初始化周邊地標搜索 Agent"""
        super().__init__("POISearchAgent")

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理周邊地標搜索請求"""
        logger.info("開始處理周邊地標搜索請求")

        try:
            # 檢查是否有旅館信息
            hotels = state.get("hotels", [])
            if not hotels:
                logger.warning("沒有旅館信息，無法搜索周邊地標")
                return {"poi_results": [], "message": "沒有旅館信息，無法搜索周邊地標"}

            poi_results = []
            # 遍歷前3個旅館，避免請求過多
            for hotel in hotels[:3]:
                hotel_id = hotel.get("id")
                hotel_name = hotel.get("name", "未知旅館")
                latitude = hotel.get("latitude")
                longitude = hotel.get("longitude")

                if not (latitude and longitude):
                    logger.warning(f"旅館 {hotel_name} 沒有地理坐標信息")
                    continue

                logger.info(f"開始搜索旅館 {hotel_name} 周邊地標")
                poi_data = await self._search_pois(latitude, longitude, hotel_name, hotel_id)
                if poi_data:
                    poi_results.append(poi_data)
        except Exception as e:
            logger.error(f"周邊地標搜索處理失敗: {e}")
            return {"poi_results": [], "message": f"周邊地標搜索失敗: {e}"}

        return {"poi_results": poi_results}

    async def _search_pois(self, latitude: float, longitude: float, hotel_name: str, hotel_id: str) -> dict[str, Any]:
        """搜索指定位置周邊的地標，利用 aiohttp 並行請求景點、餐廳與交通設施資訊"""
        try:
            async with aiohttp.ClientSession() as session:
                # 定義一個內部函數，依據類型與半徑搜索 POI
                async def fetch_poi(poi_type: str, radius: int):
                    params = {
                        "lat": latitude,
                        "lon": longitude,
                        "type": poi_type,
                        "radius": radius,
                        # 若有 API 金鑰，可加入 "key": "YOUR_API_KEY"
                    }
                    async with session.get(BASE_POI_API_URL, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("results", [])
                        logger.error(f"API請求失敗，狀態碼: {response.status}")
                        return []

                # 同時發送3個請求
                attractions, restaurants, transit = await asyncio.gather(
                    fetch_poi("attractions", 2000), fetch_poi("restaurants", 1000), fetch_poi("transit", 1000)
                )

                return {
                    "hotel_name": hotel_name,
                    "hotel_id": hotel_id,
                    "attractions": attractions,
                    "restaurants": restaurants,
                    "transport": transit,
                }
        except Exception as e:
            logger.error(f"搜索 {hotel_name} 周邊地標失敗: {e}")
            return None


# 創建周邊地標搜索Agent實例
poi_search_agent = POISearchAgent()
