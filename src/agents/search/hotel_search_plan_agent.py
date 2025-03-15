"""
旅館方案搜索 Agent 模塊

負責搜索旅館訂購方案。
"""

from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent
from src.api.services import hotel_api_service


class HotelSearchPlanAgent(BaseSubAgent):
    """旅館方案搜索Agent"""

    def __init__(self):
        """初始化"""
        super().__init__("HotelSearchPlanAgent")
        self.api_service = hotel_api_service

    async def process(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        處理旅館方案搜索

        參數:
            params (dict): 搜索參數
                - hotel_keyword (str): 旅館名稱/關鍵字
                - plan_keyword (str): 旅館訂購方案名稱/關鍵字
                - check_in_start_at (str): 退房日期 (ex. 2025-01-01)
                - check_in_end_at (str): 退房日期 (ex. 2025-01-03)

        返回:
            dict: 包含旅館方案列表的字典，格式為 {"plan_search_results": [...]}
        """
        # 確保必要的參數存在
        if not params.get("hotel_keyword"):
            logger.warning("缺少必要的參數 hotel_keyword")
            return {"plan_search_results": []}

        # 調用 API 服務搜索旅館方案
        try:
            results = await self._search_plans(params)
            return {"plan_search_results": results}
        except Exception as e:
            logger.error(f"旅館方案搜索失敗: {e}")
            return {"plan_search_results": []}

    async def _process(self, input_data: dict | str) -> dict[str, Any]:
        """處理旅館方案搜索"""
        try:
            # 如果輸入是字典，直接使用
            if isinstance(input_data, dict):
                search_params = input_data
            # 如果輸入是字符串，嘗試解析
            else:
                logger.warning("旅館方案搜索需要詳細的參數字典，而不是字符串")
                return {"plan_search_results": []}

            logger.info(f"準備搜索旅館方案，參數: {search_params}")
            results = await self._search_plans(search_params)
            return {"plan_search_results": results}
        except Exception as e:
            logger.error(f"旅館方案搜索失敗: {e}")
            return {"plan_search_results": []}

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

    # 添加 run 方法作為 process 的別名，以兼容 workflow.py 中的調用
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run 方法，作為 process 方法的別名，用於兼容 workflow.py 中的調用"""
        return await self.process(params)


# 創建旅館搜索計劃子Agent實例
hotel_search_plan_agent = HotelSearchPlanAgent()
