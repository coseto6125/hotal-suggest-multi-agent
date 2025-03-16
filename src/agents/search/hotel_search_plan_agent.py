"""
旅館方案搜索 Agent 模塊

負責搜索旅館訂購方案。
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.api.services import hotel_api_service


class HotelSearchPlanAgent(BaseAgent):
    """旅館方案搜索Agent"""

    def __init__(self):
        """初始化"""
        super().__init__("HotelSearchPlanAgent")
        self.api_service = hotel_api_service

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        處理旅館方案搜索請求
        """
        try:
            # 檢查是否有必要的搜索參數
            if not self._has_sufficient_search_conditions(state):
                logger.warning("缺少必要的方案搜索參數，無法進行方案搜索")
                return {
                    "plan_search_results": [],
                    "search_type": "none",
                    "message": "缺少必要的方案搜索參數，無法進行方案搜索",
                }

            # 處理搜索請求
            return await self._search_plans(state)
        except Exception as e:
            logger.error(f"旅館方案搜索處理失敗: {e}")
            return {"plan_search_results": [], "search_type": "error", "message": f"方案搜索處理失敗: {e!s}"}

    def _extract_search_params(self, context: dict[str, Any]) -> dict[str, Any]:
        """從context中提取搜索參數"""
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

            # 提取關鍵字
            if parsed_data.get("keywords"):
                search_params["hotel_keyword"] = parsed_data["keywords"].get("hotel_keyword", "")
                search_params["plan_keyword"] = parsed_data["keywords"].get("plan_keyword", "")

        return search_params

    async def _search_plans(self, params: dict) -> list:
        """
        調用旅館搜索計劃API
        參數:
            params (dict): 搜索參數
        """
        try:
            # 移除空參數
            search_params = {k: v for k, v in params.items() if v}

            logger.info(f"搜索旅館計劃，參數: {search_params}")
            return await self.api_service.search_plans(search_params)
        except Exception as e:
            logger.error(f"調用旅館搜索計劃API失敗: {e}")
            return []


# 創建旅館搜索計劃子Agent實例
hotel_search_plan_agent = HotelSearchPlanAgent()
