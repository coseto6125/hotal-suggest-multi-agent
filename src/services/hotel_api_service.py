"""
酒店 API 服務
"""

import random
from typing import Any

from loguru import logger

from src.config import get_config


class HotelAPIService:
    """酒店 API 服務類"""

    def __init__(self):
        """初始化酒店 API 服務"""
        config = get_config()
        self.base_url = config["api"]["base_url"]
        self.api_key = config["api"]["api_key"]
        self.timeout = config["api"]["timeout"]
        logger.info("酒店 API 服務初始化完成")

    async def search_hotels(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """
        搜索酒店

        Args:
            params: 搜索參數

        Returns:
            搜索結果列表
        """
        logger.info(f"搜索酒店，參數: {params}")

        # 由於這是一個模擬服務，我們生成一些假數據
        return self._generate_mock_hotels(params)

    def _generate_mock_hotels(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """生成模擬的酒店數據"""
        results = []

        # 根據參數生成模擬數據
        county_id = params.get("county_id", 1)  # 默認台北市
        num_results = random.randint(3, 8)  # 隨機生成3-8個結果

        county_names = {1: "台北市", 2: "新北市", 3: "桃園市", 4: "台中市", 5: "高雄市"}

        county_name = county_names.get(county_id, "未知城市")

        # 生成模擬酒店數據
        for i in range(num_results):
            hotel_price = random.randint(2000, 5000)

            # 如果有預算限制，確保價格在預算範圍內
            if params.get("budget_min") and params.get("budget_max"):
                budget_min = params.get("budget_min", 0)
                budget_max = params.get("budget_max", 10000)
                hotel_price = random.randint(budget_min, budget_max)

            hotel = {
                "hotel_id": f"MOCK_{i}_{random.randint(1000, 9999)}",
                "name": f"{county_name}測試酒店 {i + 1}",
                "address": f"{county_name}測試區測試路{random.randint(1, 100)}號",
                "city": county_name,
                "price": hotel_price,
                "rating": round(random.uniform(3.5, 4.9), 1),
                "description": "這是一個測試用的模擬酒店描述。",
                "amenities": ["WiFi", "早餐", "停車場", "游泳池"],
                "images": [f"https://example.com/mock_hotel_{i}_{j}.jpg" for j in range(1, 4)],
            }
            results.append(hotel)

        logger.info(f"生成了 {len(results)} 個模擬酒店數據")
        return results
