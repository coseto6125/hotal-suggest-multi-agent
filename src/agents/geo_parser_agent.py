"""
地理名稱解析子Agent，專門負責解析查詢中的地理名稱
"""

from typing import Any

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent
from src.cache.geo_cache import geo_cache
from src.utils.geo_parser import geo_parser


class GeoParserAgent(BaseSubAgent):
    """地理名稱解析子Agent"""

    def __init__(self):
        """初始化地理名稱解析子Agent"""
        super().__init__("GeoParserAgent")

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的地理名稱"""
        logger.info(f"解析查詢中的地理名稱: {query}")

        # 確保地理資料快取已初始化
        if not geo_cache._initialized:
            logger.info("地理資料快取尚未初始化，正在初始化...")
            await geo_cache.initialize()

        # 使用 spaCy 解析地理實體
        geo_entities = await geo_parser.parse_geo_entities(query)
        logger.info(f"從查詢中識別到的地理實體: {geo_entities}")

        # 提取縣市和鄉鎮區資訊
        destination = {
            "county": geo_entities["destination"]["county"],
            "district": geo_entities["destination"]["district"],
        }

        # 將縣市和鄉鎮區資訊轉換為名稱
        county_name = None
        district_name = None

        if destination["county"]:
            for county in geo_cache._counties:
                if county.get("id") == destination["county"]:
                    county_name = county.get("name")
                    break

        if destination["district"]:
            for district in geo_cache._districts:
                if district.get("id") == destination["district"]:
                    district_name = district.get("name")
                    break

        # 構建結果
        result = {
            "destination": destination,
            "county_name": county_name,
            "district_name": district_name,
            "county_ids": [county["id"] for county in geo_entities["counties"]],
            "district_ids": [district["id"] for district in geo_entities["districts"]],
        }

        return result


# 創建地理名稱解析子Agent實例
geo_parser_agent = GeoParserAgent()
