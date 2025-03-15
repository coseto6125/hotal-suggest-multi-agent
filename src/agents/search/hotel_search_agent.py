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

    #
    # 公共接口方法
    #
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run 方法，作為 process 方法的別名，用於兼容 workflow.py 中的調用

        參數:
            params (dict): 搜索參數

        返回:
            dict: 包含旅館列表的字典
        """
        return await self.process(params)

    async def process(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        處理旅館搜索

        參數:
            params (dict): 搜索參數
                - check_in (str): 入住日期
                - check_out (str): 退房日期
                - adults (int): 成人數
                - children (int): 兒童數
                - lowest_price (int): 最低價格
                - highest_price (int): 最高價格
                - county_ids (list): 縣市ID列表
                - district_ids (list): 區域ID列表
                - hotel_facility_ids (list): 旅館設施ID列表
                - room_facility_ids (list): 房間設施ID列表
                - has_breakfast (bool): 是否有早餐
                - has_lunch (bool): 是否有午餐
                - has_dinner (bool): 是否有晚餐
                - hotel_group_types (list): 旅館類型
                - hotel_keyword (str): 旅館關鍵字

        返回:
            dict: 包含旅館列表的字典，格式為 {"hotel_search_results": [...]}
        """
        # 檢查必要參數
        if not self._validate_required_params(params):
            return {"hotel_search_results": []}

        # 執行搜索
        try:
            result = await self._search_hotels(params)
            return result
        except Exception as e:
            logger.error(f"旅館搜索失敗: {e}")
            return {"hotel_search_results": []}

    async def _process(self, input_data: dict | str) -> dict[str, Any]:
        """
        處理輸入數據 (BaseSubAgent接口實現)

        參數:
            input_data (dict|str): 輸入數據

        返回:
            dict: 包含旅館列表的字典
        """
        if isinstance(input_data, str):
            logger.warning("收到文本輸入，尚未實現從文本提取參數的功能")
            return {"hotel_search_results": []}

        search_params = self._build_search_params(input_data)
        return await self._search_hotels(search_params)

    #
    # 核心搜索方法
    #
    async def _search_hotels(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        調用旅館搜索 API 搜索旅館

        參數:
            params (dict): 搜索參數

        返回:
            dict: 格式為 {"hotel_search_results": [...]}
        """
        try:
            # 過濾並準備API參數
            api_params = self._filter_api_params(params)

            # 檢查是否有足夠的搜索條件，避免過於寬泛的搜索
            if not self._has_sufficient_search_conditions(api_params):
                logger.warning("搜索條件過於寬泛，請提供更具體的搜索條件")
                return {"hotel_search_results": []}

            logger.info(f"搜索旅館，過濾後參數: {api_params}")

            # 執行API調用
            results = await hotel_api_service.search_hotel_vacancies(api_params)

            # 處理空結果情況
            if not results:
                logger.warning("API返回空結果")
                return {"hotel_search_results": []}

            # 關鍵字過濾（如果有指定）
            if keyword := params.get("hotel_keyword"):
                filtered_results = self._filter_by_keyword(results, keyword)
                if filtered_results:
                    return {"hotel_search_results": filtered_results}

            # 過濾有效結果
            valid_results = self._filter_valid_results(results)

            # 寬鬆搜索（如果沒有結果）
            if not valid_results:
                valid_results = await self._perform_relaxed_search(params)

            # 返回結果
            if valid_results:
                self._log_search_results(valid_results)

            return {"hotel_search_results": valid_results}

        except Exception as e:
            logger.error(f"調用旅館搜索API失敗: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {"hotel_search_results": []}

    #
    # 驗證方法
    #
    def _has_sufficient_search_conditions(self, params: dict[str, Any]) -> bool:
        """
        檢查是否有足夠的搜索條件

        參數:
            params (dict): API參數

        返回:
            bool: 是否有足夠的搜索條件
        """
        # 至少需要縣市ID或地區ID
        has_location = "county_ids" in params or "district_ids" in params

        # 如果有詳細的位置信息，則視為有足夠的搜索條件
        if has_location:
            return True

        # 如果有酒店關鍵字，也視為有足夠的搜索條件
        if params.get("hotel_keyword"):
            return True

        # 如果同時指定了入住和退房日期，也視為有足夠的搜索條件
        if "check_in" in params and "check_out" in params:
            return True

        # 否則認為條件不足
        return False

    #
    # 參數處理方法
    #
    def _validate_required_params(self, params: dict[str, Any]) -> bool:
        """
        檢查必要參數是否存在

        參數:
            params (dict): 搜索參數

        返回:
            bool: 是否包含所有必要參數
        """
        # 對於基本搜索，位置信息是最重要的
        if not params.get("county_ids") and not params.get("district_ids") and not params.get("hotel_keyword"):
            logger.warning("缺少關鍵搜索條件: 需要縣市ID、地區ID或酒店關鍵字")
            return False

        return True

    def _filter_api_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        過濾出API需要的參數，並進行必要的類型轉換

        參數:
            params (dict): 原始參數

        返回:
            dict: 過濾後的API參數
        """
        api_params = {}

        # 處理時間參數
        for date_param in ["check_in", "check_out"]:
            if params.get(date_param):
                api_params[date_param] = str(params[date_param])

        # 處理人數參數
        for int_param in ["adults", "children"]:
            if int_param in params and params[int_param] is not None:
                try:
                    api_params[int_param] = int(params[int_param])
                except (ValueError, TypeError):
                    logger.warning(f"無法將 {int_param} 轉換為整數: {params[int_param]}")
                    api_params[int_param] = 2 if int_param == "adults" else 0

        # 處理地點參數
        for location_param in ["county_ids", "district_ids"]:
            if params.get(location_param):
                location_value = params[location_param]
                if isinstance(location_value, list) and location_value:
                    api_params[location_param] = location_value
                elif not isinstance(location_value, list) and location_value:
                    api_params[location_param] = [location_value]

        # 處理價格參數
        for price_param in ["lowest_price", "highest_price"]:
            if params.get(price_param):
                try:
                    price_value = int(params[price_param])
                    if price_value > 0:
                        api_params[price_param] = price_value
                except (ValueError, TypeError):
                    logger.warning(f"無法將 {price_param} 轉換為整數: {params[price_param]}")

        # 處理布爾參數
        for bool_param in ["has_breakfast", "has_lunch", "has_dinner"]:
            if bool_param in params:
                try:
                    bool_value = bool(params[bool_param])
                    api_params[bool_param] = "1" if bool_value else "0"
                except Exception as e:
                    logger.warning(f"轉換 {bool_param} 失敗: {e}")

        # 處理其他可選參數
        if params.get("hotel_group_types"):
            api_params["hotel_group_types"] = params["hotel_group_types"]

        if params.get("hotel_keyword"):
            api_params["hotel_keyword"] = params["hotel_keyword"]

        for facility_param in ["hotel_facility_ids", "room_facility_ids"]:
            if params.get(facility_param):
                if isinstance(params[facility_param], list) and params[facility_param]:
                    api_params[facility_param] = params[facility_param]

        return api_params

    def _build_search_params(self, parsed_query: dict[str, Any]) -> dict[str, Any]:
        """
        從解析的查詢中構建搜索參數

        參數:
            parsed_query (dict): 解析後的查詢資料

        返回:
            dict: 搜索參數
        """
        params = {}

        # 處理位置信息
        if destination := parsed_query.get("destination", {}):
            params["county_ids"] = [destination.get("county")] if destination.get("county") else []
            params["district_ids"] = [destination.get("district")] if destination.get("district") else []

        # 處理日期信息
        if dates := parsed_query.get("dates", {}):
            params["check_in"] = dates.get("check_in")
            params["check_out"] = dates.get("check_out")

        # 處理人數信息
        if guests := parsed_query.get("guests", {}):
            params["adults"] = guests.get("adults", 2)
            params["children"] = guests.get("children", 0)

        # 處理預算信息
        if budget := parsed_query.get("budget", {}):
            params["lowest_price"] = budget.get("min", 0)
            params["highest_price"] = budget.get("max", 0)

        # 處理旅館類型
        if hotel_type := parsed_query.get("hotel_type"):
            params["hotel_group_types"] = [hotel_type]

        # 處理特殊需求
        if facilities := parsed_query.get("special_requirements", []):
            params["hotel_facility_ids"] = facilities

        # 處理關鍵字搜索
        if keyword := parsed_query.get("keyword"):
            params["hotel_keyword"] = keyword

        return params

    def _build_relaxed_search_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        構建更寬鬆的搜索參數，降低搜索條件

        參數:
            params (dict): 原始搜索參數

        返回:
            dict: 寬鬆搜索參數
        """
        relaxed_params = params.copy()

        # 確保至少保留縣市ID或關鍵字，否則搜索範圍太大
        if not relaxed_params.get("county_ids") and not relaxed_params.get("hotel_keyword"):
            logger.warning("無法執行寬鬆搜索: 原始參數中缺少縣市ID或關鍵字")
            return relaxed_params

        # 移除限制較嚴格的條件
        for key in [
            "district_ids",
            "lowest_price",
            "highest_price",
            "hotel_facility_ids",
            "room_facility_ids",
            "has_breakfast",
            "has_lunch",
            "has_dinner",
        ]:
            relaxed_params.pop(key, None)

        # 如果有多個縣市，只保留第一個
        if county_ids := relaxed_params.get("county_ids"):
            if isinstance(county_ids, list) and len(county_ids) > 1:
                relaxed_params["county_ids"] = [county_ids[0]]

        return relaxed_params

    #
    # 結果處理方法
    #
    def _filter_by_keyword(self, results: list, keyword: str) -> list:
        """
        使用關鍵字過濾旅館結果

        參數:
            results (list): 旅館結果列表
            keyword (str): 關鍵字

        返回:
            list: 過濾後的旅館列表
        """
        if not keyword or len(keyword) <= 1:
            return results

        logger.info(f"使用關鍵字「{keyword}」過濾旅館")
        filtered_results = [
            hotel
            for hotel in results
            if isinstance(hotel, dict) and "name" in hotel and keyword.lower() in hotel["name"].lower()
        ]

        if filtered_results:
            logger.success(f"找到 {len(filtered_results)} 間名稱包含「{keyword}」的旅館")
            return filtered_results

        logger.warning(f"未找到名稱包含「{keyword}」的旅館，返回所有結果")
        return []

    def _filter_valid_results(self, results: list) -> list:
        """
        過濾有效的旅館結果

        參數:
            results (list): 旅館結果列表

        返回:
            list: 有效的旅館列表
        """
        if not results:
            return []

        # 過濾掉包含error_message的結果和非字典結果
        valid_results = [hotel for hotel in results if isinstance(hotel, dict) and "error_message" not in hotel]

        # 驗證數據結構
        valid_hotels = []
        required_fields = ["id", "name", "address"]

        for hotel in valid_results:
            missing_fields = [field for field in required_fields if field not in hotel]
            if missing_fields:
                logger.warning(f"旅館 {hotel.get('id', 'unknown')} 缺少必要欄位: {missing_fields}")
                continue
            valid_hotels.append(hotel)

        return valid_hotels

    async def _perform_relaxed_search(self, params: dict[str, Any]) -> list:
        """
        執行寬鬆條件的搜索

        參數:
            params (dict): 原始搜索參數

        返回:
            list: 搜索結果
        """
        logger.info("未找到有效旅館，嘗試使用更寬鬆的條件")
        relaxed_params = self._build_relaxed_search_params(params)

        # 檢查寬鬆參數是否有效
        if not relaxed_params.get("county_ids") and not relaxed_params.get("hotel_keyword"):
            logger.warning("寬鬆搜索參數無效，無法執行寬鬆搜索")
            return []

        relaxed_api_params = self._filter_api_params(relaxed_params)

        logger.info(f"使用寬鬆參數搜索: {relaxed_api_params}")
        results = await hotel_api_service.search_hotel_vacancies(relaxed_api_params)

        return self._filter_valid_results(results)

    def _log_search_results(self, results: list) -> None:
        """
        記錄搜索結果

        參數:
            results (list): 旅館結果列表
        """
        logger.info(f"搜索到 {len(results)} 個有效旅館")
        if results:
            hotel_names = [h.get("name", "未命名") for h in results[:3]]
            logger.info(f"有效旅館示例: {', '.join(hotel_names)}")


# 創建旅館搜索Agent實例
hotel_search_agent = HotelSearchAgent()
