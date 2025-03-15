"""
旅館模糊搜索 Agent 模塊

負責根據名稱模糊搜索旅館。
"""

from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent
from src.api.services import hotel_api_service


class HotelSearchFuzzyAgent(BaseSubAgent):
    """旅館模糊搜索子Agent"""

    def __init__(self):
        """初始化旅館模糊搜索子Agent"""
        super().__init__("HotelSearchFuzzyAgent")

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢，調用HotelAPIService.fuzzy_match_hotel API"""
        logger.info(f"調用旅館模糊搜索API: {query}")

        # TODO: 實現旅館模糊搜索API調用邏輯
        # 從context中提取關鍵字
        keywords = self._extract_keywords(context)

        # 調用API
        fuzzy_results = await self._fuzzy_match_hotel(keywords)

        return {"fuzzy_results": fuzzy_results}

    def _extract_keywords(self, context: dict[str, Any]) -> list[str]:
        """從context中提取關鍵字"""
        # TODO: 實現從context中提取關鍵字的邏輯
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
        # TODO: 實現調用HotelAPIService.fuzzy_match_hotel API的邏輯
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

    async def process(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        處理旅館模糊搜索

        參數:
            params (dict): 搜索參數
                - hotel_name (str): 旅館名稱/關鍵字

        返回:
            dict: 包含旅館列表的字典，格式為 {"fuzzy_search_results": [...]}
        """
        # 確保必要的參數存在
        if not params.get("hotel_name"):
            logger.warning("缺少必要的參數 hotel_name")
            return {"fuzzy_search_results": []}

        # 調用 API 服務模糊搜索旅館
        try:
            results = await self._fuzzy_match(params)
            return {"fuzzy_search_results": results}
        except Exception as e:
            logger.error(f"旅館模糊搜索失敗: {e}")
            return {"fuzzy_search_results": []}

    # 添加 run 方法作為 process 的別名，以兼容 workflow.py 中的調用
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run 方法，作為 process 方法的別名，用於兼容 workflow.py 中的調用"""
        return await self.process(params)

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
