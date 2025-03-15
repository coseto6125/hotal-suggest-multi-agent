"""
周邊地標搜索Agent，負責搜索周邊地標
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.api.services import poi_api_service


class POISearchAgent(BaseAgent):
    """周邊地標搜索Agent"""

    def __init__(self):
        """初始化周邊地標搜索Agent"""
        super().__init__("POISearchAgent")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理周邊地標搜索"""
        # TODO: 實現周邊地標搜索邏輯
        hotels = inputs.get("hotels", [])

        if not hotels:
            return {"error": "旅館列表為空"}

        logger.info(f"搜索周邊地標，旅館數量: {len(hotels)}")

        # 只處理前3個旅館的周邊地標
        poi_results = []
        for hotel in hotels[:3]:
            hotel_name = hotel.get("name", "")
            if hotel_name:
                # 搜索周邊景點
                attractions_query = f"{hotel_name}附近的景點"
                attractions = await poi_api_service.search_nearby_places(attractions_query)

                # 搜索周邊餐廳
                restaurants_query = f"{hotel_name}附近的餐廳"
                restaurants = await poi_api_service.search_nearby_places(restaurants_query)

                # 搜索周邊交通
                transport_query = f"{hotel_name}附近的交通"
                transport = await poi_api_service.search_nearby_places(transport_query)

                poi_results.append(
                    {
                        "hotel_name": hotel_name,
                        "hotel_id": hotel.get("id", ""),
                        "attractions": attractions,
                        "restaurants": restaurants,
                        "transport": transport,
                    }
                )

        return {"poi_results": poi_results}


# 創建周邊地標搜索Agent實例
poi_search_agent = POISearchAgent()
