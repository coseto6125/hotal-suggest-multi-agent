"""
查詢解析Agent，負責解析用戶查詢
"""

from typing import Any

from loguru import logger
from opencc import OpenCC

from src.agents.base_agent import BaseAgent
from src.cache.geo_cache import geo_cache
from src.services.llm_service import llm_service
from src.utils.geo_parser import geo_parser


class QueryParserAgent(BaseAgent):
    """查詢解析Agent"""

    def __init__(self):
        """初始化查詢解析Agent"""
        super().__init__("QueryParserAgent")
        self.cc = OpenCC("s2twp")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理用戶查詢"""
        user_query = inputs.get("user_query", "")
        user_query = self.cc.convert(user_query)

        if not user_query:
            return {"error": "用戶查詢為空"}

        logger.info(f"解析用戶查詢: {user_query}")

        # 確保地理資料快取已初始化
        if not geo_cache._initialized:
            logger.info("地理資料快取尚未初始化，正在初始化...")
            await geo_cache.initialize()

        # 使用 spaCy 解析地理實體 - 不需要重新初始化 geo_parser
        geo_entities = await geo_parser.parse_geo_entities(user_query)
        logger.info(f"從查詢中識別到的地理實體: {geo_entities}")

        # 使用LLM解析用戶查詢，傳遞已解析的地理實體，避免重複解析
        parsed_query = await llm_service.parse_user_query(user_query, geo_entities)

        # 將已解析的地理實體保存到 parsed_query 中，以便後續使用
        parsed_query["geo_entities"] = geo_entities
        parsed_query["original_query"] = user_query

        # 使用地理名稱解析器增強解析結果
        enhanced_query = await geo_parser.enhance_query_with_geo_data(parsed_query)

        # 驗證解析結果中的地理資料
        self._validate_geo_data(enhanced_query)

        # 移除臨時使用的 geo_entities 字段，避免返回不必要的數據
        if "geo_entities" in enhanced_query:
            del enhanced_query["geo_entities"]

        return {"parsed_query": enhanced_query, "original_query": user_query}

    def _validate_geo_data(self, parsed_query: dict[str, Any]) -> None:
        """驗證並修正解析結果中的地理資料"""
        if not parsed_query or "destination" not in parsed_query:
            return

        destination = parsed_query.get("destination", {})
        if not destination:
            return

        # 獲取縣市和鄉鎮區
        county_id = destination.get("county")
        district_id = destination.get("district")

        # 如果縣市ID無效，嘗試查找有效的ID
        if county_id and not any(county.get("id") == county_id for county in geo_cache._counties):
            logger.warning(f"無效的縣市ID: {county_id}，嘗試查找有效的ID")
            # 嘗試將縣市名稱轉換為ID
            county = geo_cache.get_county_by_name(county_id)
            if county:
                destination["county"] = county.get("id")
                logger.info(f"將縣市名稱 '{county_id}' 轉換為ID: {county.get('id')}")
            else:
                logger.warning(f"無法找到縣市: {county_id}")
                destination["county"] = None

        # 如果鄉鎮區ID無效，嘗試查找有效的ID
        if district_id and not any(district.get("id") == district_id for district in geo_cache._districts):
            logger.warning(f"無效的鄉鎮區ID: {district_id}，嘗試查找有效的ID")
            # 嘗試將鄉鎮區名稱轉換為ID
            district = geo_cache.get_district_by_name(district_id)
            if district:
                destination["district"] = district.get("id")
                logger.info(f"將鄉鎮區名稱 '{district_id}' 轉換為ID: {district.get('id')}")
            else:
                logger.warning(f"無法找到鄉鎮區: {district_id}")
                destination["district"] = None


# 創建查詢解析Agent實例
query_parser_agent = QueryParserAgent()
