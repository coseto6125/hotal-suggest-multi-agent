"""
旅館搜索計劃子Agent，專門負責調用HotelAPIService.search_plans API
"""

from typing import Any, list

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent
from src.api.services import hotel_api_service


class HotelSearchPlanAgent(BaseSubAgent):
    """旅館搜索計劃子Agent"""

    def __init__(self):
        """初始化旅館搜索計劃子Agent"""
        super().__init__("HotelSearchPlanAgent")

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢，調用HotelAPIService.search_plans API"""
        logger.info(f"調用旅館搜索計劃API: {query}")

        # TODO: 實現旅館搜索計劃API調用邏輯
        # 從context中提取搜索參數
        search_params = self._extract_search_params(context)

        # 調用API
        search_results = await self._search_plans(search_params)

        return {"search_results": search_results}

    def _extract_search_params(self, context: dict[str, Any]) -> dict[str, Any]:
        """從context中提取搜索參數"""
        # TODO: 實現從context中提取搜索參數的邏輯
        search_params = {}

        # 提取必要參數
        if "parsed_data" in context:
            parsed_data = context["parsed_data"]

            # 提取日期信息
            if parsed_data.get("dates"):
                search_params["check_in"] = parsed_data["dates"].get("check_in")
                search_params["check_out"] = parsed_data["dates"].get("check_out")

            # 提取人數信息
            if parsed_data.get("guests"):
                search_params["adults"] = parsed_data["guests"].get("adults", 2)
                search_params["children"] = parsed_data["guests"].get("children", 0)

            # 提取預算信息
            if parsed_data.get("budget"):
                search_params["lowest_price"] = parsed_data["budget"].get("min")
                search_params["highest_price"] = parsed_data["budget"].get("max")

            # 提取地理信息
            if parsed_data.get("geo"):
                search_params["county_ids"] = parsed_data["geo"].get("county_ids", [])
                search_params["district_ids"] = parsed_data["geo"].get("district_ids", [])

            # 提取設施信息
            if parsed_data.get("facilities"):
                search_params["hotel_facility_ids"] = parsed_data["facilities"].get("hotel_facility_ids", [])
                search_params["room_facility_ids"] = parsed_data["facilities"].get("room_facility_ids", [])

            # 提取房型信息
            if parsed_data.get("room_types"):
                search_params["room_types"] = parsed_data["room_types"]

            # 提取餐食信息
            if parsed_data.get("food_req"):
                search_params["has_breakfast"] = parsed_data["food_req"].get("has_breakfast", False)
                search_params["has_lunch"] = parsed_data["food_req"].get("has_lunch", False)
                search_params["has_dinner"] = parsed_data["food_req"].get("has_dinner", False)

            # 提取旅館類型信息
            if parsed_data.get("hotel_type"):
                search_params["hotel_group_types"] = parsed_data["hotel_type"]

        return search_params

    async def _search_plans(self, search_params: dict[str, Any]) -> list[dict[str, Any]]:
        """調用HotelAPIService.search_plans API"""
        # TODO: 實現調用HotelAPIService.search_plans API的邏輯
        try:
            # 調用API
            search_results = await hotel_api_service.search_plans(
                check_in=search_params.get("check_in"),
                check_out=search_params.get("check_out"),
                adults=search_params.get("adults", 2),
                children=search_params.get("children", 0),
                lowest_price=search_params.get("lowest_price"),
                highest_price=search_params.get("highest_price"),
                county_ids=search_params.get("county_ids", []),
                district_ids=search_params.get("district_ids", []),
                hotel_facility_ids=search_params.get("hotel_facility_ids", []),
                room_types=search_params.get("room_types", []),
                room_facility_ids=search_params.get("room_facility_ids", []),
                has_breakfast=search_params.get("has_breakfast", False),
                has_lunch=search_params.get("has_lunch", False),
                has_dinner=search_params.get("has_dinner", False),
                hotel_group_types=search_params.get("hotel_group_types"),
            )

            logger.info(f"搜索到 {len(search_results)} 個旅館計劃")
            return search_results
        except Exception as e:
            logger.error(f"調用旅館搜索計劃API失敗: {e!s}")
            return []


# 創建旅館搜索計劃子Agent實例
hotel_search_plan_agent = HotelSearchPlanAgent()
