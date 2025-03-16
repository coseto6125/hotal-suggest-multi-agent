"""
地理名稱解析子Agent，專門負責解析查詢中的地理名稱
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.cache.geo_cache import geo_cache
from src.utils.geo_parser import geo_parser


class GeoParserAgent(BaseAgent):
    """地理名稱解析子Agent"""

    def __init__(self):
        """初始化地理名稱解析子Agent"""
        super().__init__("GeoParserAgent")

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        處理地理名稱解析請求
        """
        logger.debug(f"[{self.name}] 開始處理地理名稱解析請求")

        # 從輸入中提取查詢和上下文
        query = state.get("query", "")
        context = state.get("context", {})
        result = {}

        try:
            if not query:
                # 如果沒有查詢文本，嘗試從上下文或其他字段獲取信息
                if "destination" in context:
                    result = {"destination": context["destination"], "geo_parsed": True}
                    return result

                logger.warning("查詢內容為空，無法解析地理名稱")
                result = {
                    "destination": {"county": None, "district": None},
                    "county_name": None,
                    "district_name": None,
                    "county_ids": [],
                    "district_ids": [],
                    "message": "查詢內容為空，無法解析地理名稱",
                    "geo_parsed": False,
                }
                return result

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

            # 組織返回數據
            result = {
                "geo_data": {
                    "county_id": geo_entities["destination"]["county"],
                    "district_id": geo_entities["destination"]["district"],
                },
                "destination": destination,
                "counties": geo_entities["counties"],
                "districts": geo_entities["districts"],
                "geo_parsed": True,  # 添加解析完成標誌
            }

            # 如果有縣市信息，添加到縣市ID列表
            if geo_entities["destination"]["county"]:
                result["county_ids"] = [geo_entities["destination"]["county"]]

                # 查找縣市名稱
                county_name = None
                for county in geo_entities["counties"]:
                    if county["id"] == geo_entities["destination"]["county"]:
                        county_name = county["name"]
                        break
                result["county_name"] = county_name

            # 如果有鄉鎮區信息，添加到鄉鎮區ID列表
            if geo_entities["destination"]["district"]:
                result["district_ids"] = [geo_entities["destination"]["district"]]

                # 查找鄉鎮區名稱
                district_name = None
                for district in geo_entities["districts"]:
                    if district["id"] == geo_entities["destination"]["district"]:
                        district_name = district["name"]
                        break
                result["district_name"] = district_name

            return result

        except Exception as e:
            logger.error(f"解析地理名稱時出錯: {e!s}")
            # 返回空結果並標記解析失敗
            return {
                "destination": {"county": None, "district": None},
                "message": f"解析地理名稱時出錯: {e!s}",
                "geo_parsed": False,
            }
