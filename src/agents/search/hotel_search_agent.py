"""
旅館搜索 Agent 模塊

負責根據用戶查詢參數搜索旅館。
"""

from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent
from src.api.services import hotel_api_service


class HotelSearchAgent(BaseSubAgent):
    """旅館搜索Agent"""

    def __init__(self):
        """初始化旅館搜索Agent"""
        super().__init__("HotelSearchAgent")

    async def process(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        處理旅館搜索

        參數:
            params (dict): 搜索參數
                - hotel_group_types (str): 旅館類別
                - check_in (str): 入住日期
                - check_out (str): 退房日期
                - adults (int): 成人數
                - children (int): 兒童數
                - lowest_price (int): 最低價格
                - highest_price (int): 最高價格
                - county_ids[] (list): The IDs of the counties to search in
                - district_ids[] (list): The IDs of the districts to search in
                - hotel_facility_ids[] (list): 旅館設施ID列表
                - room_facility_ids[] (list): 房間設施ID列表
                - has_breakfast (bool): 是否有早餐
                - has_lunch (bool): 是否有午餐
                - has_dinner (bool): 是否有晚餐

        返回:
            dict: 包含旅館列表的字典，格式為 {"hotel_search_results": [...]}
        """
        # 確保必要的參數存在
        required_params = ["check_in", "check_out", "adults", "children"]
        for param in required_params:
            if param not in params:
                logger.warning(f"缺少必要的參數 {param}")
                return {"hotel_search_results": []}

        # 調用 API 服務搜索旅館
        try:
            return await self._search_hotels(params)
        except Exception as e:
            logger.error(f"旅館搜索失敗: {e}")
            return {"hotel_search_results": []}

    async def _process(self, input_data: dict | str) -> dict[str, Any]:
        """
        處理輸入數據

        參數:
            input_data (dict|str): 輸入數據

        返回:
            dict: 包含旅館列表的字典，格式為 {"hotel_search_results": [...]}
        """
        if isinstance(input_data, str):
            # 如果輸入是字符串，假設是查詢文本
            # TODO: 實現從文本中提取搜索參數的邏輯
            return {"hotel_search_results": []}

        # 構建搜索參數
        search_params = self._build_search_params(input_data)

        # 調用搜索方法
        return await self._search_hotels(search_params)

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

    async def _search_hotels(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        調用旅館搜索 API 搜索旅館
        """
        try:
            # 確保整數型參數類型正確
            for int_param in ["adults", "children"]:
                if int_param in params and params[int_param] is not None:
                    params[int_param] = int(params[int_param])

            # 確保布爾型參數類型正確 - 轉換為字符串，因為 API 不接受布爾值
            for bool_param in ["has_breakfast", "has_lunch", "has_dinner"]:
                if bool_param in params:
                    # 將布爾值轉換為字符串 "1" 或 "0"
                    params[bool_param] = "1" if params[bool_param] else "0"

            # 移除空參數 (None 或空字符串)
            search_params = {k: v for k, v in params.items() if v is not None and v != ""}

            logger.info(f"搜索旅館，參數: {search_params}")
            results = await hotel_api_service.search_hotel_vacancies(search_params)

            # 過濾掉包含error_message的結果，這些不是實際的旅館
            valid_results = [hotel for hotel in results if "error_message" not in hotel]

            # 如果沒有找到旅館，嘗試使用更寬鬆的條件
            if not valid_results:
                logger.info("未找到有效旅館，嘗試使用更寬鬆的條件")
                relaxed_params = self._build_relaxed_search_params(params)
                results = await hotel_api_service.search_hotel_vacancies(relaxed_params)
                valid_results = [hotel for hotel in results if "error_message" not in hotel]

            logger.info(f"搜索到 {len(valid_results)} 個有效旅館")
            # 返回字典格式，而不是直接返回列表
            return {"hotel_search_results": valid_results}
        except Exception as e:
            logger.error(f"調用旅館搜索 API 失敗: {e}")
            # 返回空列表的字典格式
            return {"hotel_search_results": []}

    # 添加 run 方法作為 process 的別名，以兼容 workflow.py 中的調用
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run 方法，作為 process 方法的別名，用於兼容 workflow.py 中的調用"""
        return await self.process(params)


# 創建旅館搜索Agent實例
hotel_search_agent = HotelSearchAgent()
