"""
旅館搜索Agent，負責搜索旅館
"""

from typing import Any

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.api.services import hotel_api_service


class HotelSearchAgent(BaseAgent):
    """旅館搜索Agent"""

    def __init__(self):
        """初始化旅館搜索Agent"""
        super().__init__("HotelSearchAgent")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理旅館搜索"""
        # TODO: 實現旅館搜索邏輯
        parsed_query = inputs.get("parsed_query", {})

        if not parsed_query:
            return {"error": "解析後的查詢為空"}

        logger.info(f"搜索旅館: {parsed_query}")

        # 構建搜索參數
        search_params = self._build_search_params(parsed_query)

        # 搜索旅館
        hotels = await hotel_api_service.search_hotel_vacancies(search_params)

        # 如果沒有找到旅館，嘗試使用更寬鬆的條件
        if not hotels:
            logger.info("未找到旅館，嘗試使用更寬鬆的條件")
            search_params = self._build_relaxed_search_params(parsed_query)
            hotels = await hotel_api_service.search_hotel_vacancies(search_params)

        # 獲取旅館詳情
        hotel_details = []
        for hotel in hotels[:5]:  # 只處理前5個旅館
            hotel_id = hotel.get("id")
            if hotel_id:
                detail = await hotel_api_service.get_hotel_detail(hotel_id)
                hotel_details.append(detail)

        return {"hotels": hotels, "hotel_details": hotel_details, "search_params": search_params}

    def _build_search_params(self, parsed_query: dict[str, Any]) -> dict[str, Any]:
        """構建搜索參數"""
        # TODO: 實現構建搜索參數的邏輯
        params = {}

        # 目的地
        destination = parsed_query.get("destination", {})
        if destination:
            params["county_id"] = destination.get("county")
            params["district_id"] = destination.get("district")

        # 日期
        dates = parsed_query.get("dates", {})
        if dates:
            params["check_in_date"] = dates.get("check_in")
            params["check_out_date"] = dates.get("check_out")

        # 人數
        guests = parsed_query.get("guests", {})
        if guests:
            params["adults"] = guests.get("adults")
            params["children"] = guests.get("children")

        # 預算
        budget = parsed_query.get("budget", {})
        if budget:
            params["min_price"] = budget.get("min")
            params["max_price"] = budget.get("max")

        # 旅館類型
        hotel_type = parsed_query.get("hotel_type")
        if hotel_type:
            params["hotel_type_id"] = hotel_type

        # 特殊需求
        special_requirements = parsed_query.get("special_requirements", [])
        if special_requirements:
            params["facilities"] = special_requirements

        return params

    def _build_relaxed_search_params(self, parsed_query: dict[str, Any]) -> dict[str, Any]:
        """構建更寬鬆的搜索參數"""
        # TODO: 實現構建更寬鬆搜索參數的邏輯
        params = self._build_search_params(parsed_query)

        # 移除一些限制條件
        params.pop("district_id", None)
        params.pop("min_price", None)
        params.pop("max_price", None)
        params.pop("hotel_type_id", None)
        params.pop("facilities", None)

        return params


# 創建旅館搜索Agent實例
hotel_search_agent = HotelSearchAgent()
