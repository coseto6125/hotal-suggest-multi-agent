"""
旅館模糊搜索 Agent 模塊

負責根據名稱模糊搜索旅館。
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.api.services import hotel_api_service


class HotelSearchFuzzyAgent(BaseAgent):
    """旅館模糊搜索子Agent"""

    def __init__(self):
        """初始化旅館模糊搜索子Agent"""
        super().__init__("HotelSearchFuzzyAgent")

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        處理模糊旅館搜索請求
        """
        try:
            # 檢查是否有旅館名稱或關鍵字
            hotel_name = state.get("hotel_name", "")
            hotel_keyword = state.get("hotel_keyword", "")

            keyword = hotel_name or hotel_keyword

            if not keyword:
                logger.warning("缺少旅館名稱或關鍵字，無法進行模糊搜索")
                return {
                    "fuzzy_search_results": [],
                    "search_type": "none",
                    "message": "缺少旅館名稱或關鍵字，無法進行模糊搜索",
                }

            # 構建搜索參數
            search_params = {"hotel_name": keyword}

            # 進行模糊搜索
            fuzzy_results = await self._fuzzy_match(search_params)

            # 處理搜索結果
            if fuzzy_results:
                logger.info(f"模糊搜索到 {len(fuzzy_results)} 個旅館")
                # 提取旅館名稱
                hotel_names = [hotel.get("name") for hotel in fuzzy_results if hotel.get("name")]
                return {
                    "fuzzy_search_results": fuzzy_results,
                    "search_type": "fuzzy",
                    "message": f"使用關鍵字 '{keyword}' 模糊搜索到相關旅館",
                    "llm_recommend_hotel": hotel_names[:3],  # 只取前三個
                }
            logger.warning(f"使用關鍵字 '{keyword}' 未找到相關旅館")
            return {
                "fuzzy_search_results": [],
                "search_type": "none",
                "message": f"使用關鍵字 '{keyword}' 未找到相關旅館",
            }
        except Exception as e:
            logger.error(f"旅館模糊搜索處理失敗: {e}")
            return {"fuzzy_search_results": [], "search_type": "error", "message": f"模糊搜索處理失敗: {e!s}"}

    def _extract_keywords(self, context: dict[str, Any]) -> list[str]:
        """從context中提取關鍵字"""
        keywords = []

        # 提取關鍵字
        if "parsed_data" in context and "keywords" in context["parsed_data"]:
            keywords = context["parsed_data"]["keywords"]

        # 如果沒有關鍵字，嘗試從原始查詢中提取
        if not keywords and "original_query" in context:
            # 這裡只是一個簡單的示例，實際應用中可能需要更複雜的邏輯
            query = context["original_query"]
            # 移除常見的停用詞
            stop_words = ["我", "想", "要", "找", "一個", "一家", "有", "的", "旅館", "飯店", "旅館", "住宿"]
            for word in stop_words:
                query = query.replace(word, " ")

            # 分割查詢並過濾空字符串
            keywords = [k.strip() for k in query.split() if k.strip()]

        return keywords

    async def _fuzzy_match_hotel(self, keywords: list[str]) -> list[dict[str, Any]]:
        """調用HotelAPIService.fuzzy_match_hotel API"""
        if not keywords:
            logger.warning("沒有提供關鍵字，無法進行模糊搜索")
            return []

        try:
            # 將關鍵字列表轉換為單個字符串
            keyword_str = " ".join(keywords)

            # 調用API
            fuzzy_results = await hotel_api_service.fuzzy_match_hotel(keyword_str)

            logger.info(f"模糊搜索到 {len(fuzzy_results)} 個旅館")
            return fuzzy_results
        except Exception as e:
            logger.error(f"調用旅館模糊搜索API失敗: {e!s}")
            return []

    async def _fuzzy_match(self, params: dict) -> list[dict[str, Any]]:
        """使用旅館名稱進行模糊匹配"""
        try:
            hotel_name = params.get("hotel_name", "")
            if not hotel_name:
                logger.warning("旅館名稱為空，無法進行模糊匹配")
                return []

            logger.info(f"使用名稱 '{hotel_name}' 進行模糊匹配")
            return await hotel_api_service.fuzzy_match_hotel({"hotel_name": hotel_name})
        except Exception as e:
            logger.error(f"模糊匹配失敗: {e}")
            return []


# 創建旅館模糊搜索子Agent實例
hotel_search_fuzzy_agent = HotelSearchFuzzyAgent()
