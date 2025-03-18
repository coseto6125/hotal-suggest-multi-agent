"""
周邊地標搜索 Agent 模塊
負責搜索旅館附近的地標，如景點、餐廳和交通設施。
"""

import asyncio
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.api.services import poi_api_service


class POISearchAgent(BaseAgent):
    """周邊地標搜索 Agent"""

    def __init__(self):
        """初始化周邊地標搜索 Agent"""
        super().__init__("POISearchAgent")

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理周邊地標搜索請求"""
        logger.info("開始處理周邊地標搜索請求")

        try:
            # 檢查是否有LLM推薦的Hotel
            # state["llm_recommend_hotel"] = ["雀客藏居台北南港","雀客藏居台北陽明山"] # ! mock data
            llm_recommend_hotel = state.get("llm_recommend_hotel", [])
            logger.info(f"接收到的 llm_recommend_hotel: {llm_recommend_hotel}")

            if not llm_recommend_hotel:
                logger.warning("沒有LLM推薦的POI，無法搜索周邊地標")
                return {
                    "poi_results": [],
                    "surroundings_map_images": [],
                    "message": "沒有LLM推薦的POI，無法搜索周邊地標",
                }

            # 檢查是否有旅館信息
            hotels = (
                state.get("hotel_search_results", [])
                or state.get("fuzzy_search_results", [])
                or state.get("plan_search_results", [])
            )
            logger.info(f"找到 {len(hotels)} 間旅館進行周邊搜索")

            if not hotels:
                logger.warning("沒有旅館信息，無法搜索周邊地標")
                return {"poi_results": [], "message": "沒有旅館信息，無法搜索周邊地標"}

            poi_results = []
            surroundings_map_images = []

            # 遍歷前3個旅館，避免請求過多
            for hotel in hotels[:3]:
                hotel_id = hotel.get("id")
                hotel_name = hotel.get("name", "未知旅館")

                logger.info(f"開始搜索旅館 {hotel_name} 周邊地標")

                # 為每個旅館搜索推薦的POI
                hotel_poi_results = await self._search_pois_for_hotel(hotel_name, hotel_id, llm_recommend_hotel)
                if hotel_poi_results:
                    poi_results.append(hotel_poi_results)

                    # 如果有地圖圖片，添加到結果中
                    if "map_image" in hotel_poi_results:
                        surroundings_map_images.append(
                            {"hotel_name": hotel_name, "hotel_id": hotel_id, "image": hotel_poi_results["map_image"]}
                        )
        except Exception as e:
            logger.error(f"周邊地標搜索處理失敗: {e}")
            return {"poi_results": [], "surroundings_map_images": [], "message": f"周邊地標搜索失敗: {e}"}

        return {"poi_results": poi_results, "surroundings_map_images": surroundings_map_images}

    async def _search_pois_for_hotel(self, hotel_name: str, hotel_id: str, poi_keywords: list[str]) -> dict[str, Any]:
        """搜索指定旅館周邊的地標，使用poi_api_service並行請求多個POI"""
        try:
            # 定義一個內部函數，搜索特定關鍵字的POI
            async def fetch_poi(keyword: str):
                try:
                    result = await poi_api_service.search_nearby_places(f"{hotel_name} 附近 {keyword}")
                    return {"keyword": keyword, "places": result.get("places", [])}
                except Exception as e:
                    logger.error(f"搜索 {hotel_name} 附近的 {keyword} 失敗: {e}")
                    return {"keyword": keyword, "places": []}

            # 同時發送多個POI關鍵字請求
            poi_tasks = [fetch_poi(keyword) for keyword in poi_keywords[:5]]  # 限制最多5個關鍵字
            poi_results = await asyncio.gather(*poi_tasks)

            # 整理結果
            categorized_pois = {}
            for result in poi_results:
                if result["places"]:
                    logger.debug(f"整理結果: {result['keyword']} - {result['places']}")
                    categorized_pois[result["keyword"]] = result["places"]

            return {
                "hotel_name": hotel_name,
                "hotel_id": hotel_id,
                "pois": categorized_pois,
                "map_image": f"map_{hotel_id}_{poi_keywords[0]}.png",  # 假設有地圖圖片
            }
        except Exception as e:
            logger.error(f"搜索 {hotel_name} 周邊地標失敗: {e}")
            return None


# 創建周邊地標搜索Agent實例
poi_search_agent = POISearchAgent()
