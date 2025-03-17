"""
旅館搜索 Agent 模塊

負責根據解析後的搜索條件搜索旅館。
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.api.services import hotel_api_service


class HotelSearchAgent(BaseAgent):
    """旅館搜索Agent"""

    def __init__(self):
        """初始化旅館搜索Agent"""
        super().__init__("HotelSearchAgent")
        self.api_service = hotel_api_service

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        處理旅館搜索請求
        """
        try:
            # 首先檢查是否有預設的搜索參數
            search_params = state.get("hotel_search_params", {})

            # 如果有預設參數，使用它
            if search_params:
                logger.info(f"使用預設搜索參數: {search_params}")
                return await self._search_hotels(search_params)

            # 否則檢查輸入是否有足夠的搜索條件
            if not self._has_sufficient_search_conditions(state):
                logger.warning("搜索條件不足，無法進行旅館搜索")
                return {"hotel_search_results": [], "search_type": "none", "message": "搜索條件不足，無法進行旅館搜索"}

            # 處理搜索請求
            return await self._search_hotels(state)
        except Exception as e:
            logger.error(f"旅館搜索處理失敗: {e}")
            return {"hotel_search_results": [], "search_type": "error", "message": f"搜索處理失敗: {e!s}"}

    async def _search_hotels(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        搜索旅館
        """
        # 驗證必要的參數
        if not self._validate_required_params(params):
            logger.warning("缺少必要的參數，無法進行旅館搜索")
            return {"hotel_search_results": [], "search_type": "none", "message": "缺少必要的參數，無法進行旅館搜索"}

        # 篩選API參數
        api_params = self._filter_api_params(params)
        logger.info(f"旅館搜索參數: {api_params}")

        # 嘗試使用提供的參數進行搜索
        try:
            results = await self.api_service.search_hotels(api_params)
            if results:
                # 過濾有效結果
                filtered_results = self._filter_valid_results(results)
                if filtered_results:
                    self._log_search_results(filtered_results)
                    # 提取旅館名稱並保存到 llm_recommend_hotel
                    hotel_names = [hotel.get("name") for hotel in filtered_results if hotel.get("name")]
                    return {
                        "hotel_search_results": filtered_results,
                        "search_type": "exact",
                        "message": "成功找到符合條件的旅館",
                        "llm_recommend_hotel": hotel_names[:3],  # 只取前三個
                    }

            # 如果有關鍵字，嘗試使用關鍵字過濾
            if params.get("hotel_keyword"):
                keyword = params["hotel_keyword"]
                relaxed_results = await self._perform_relaxed_search(params)
                filtered_by_keyword = self._filter_by_keyword(relaxed_results, keyword)
                if filtered_by_keyword:
                    self._log_search_results(filtered_by_keyword)
                    # 提取旅館名稱並保存到 llm_recommend_hotel
                    hotel_names = [hotel.get("name") for hotel in filtered_by_keyword if hotel.get("name")]
                    return {
                        "hotel_search_results": filtered_by_keyword,
                        "search_type": "keyword",
                        "message": f"使用關鍵字 '{keyword}' 找到相關旅館",
                        "llm_recommend_hotel": hotel_names[:3],  # 只取前三個
                    }

            # 嘗試使用放寬條件的搜索
            relaxed_params = self._build_relaxed_search_params(params)
            logger.info(f"使用放寬條件進行搜索: {relaxed_params}")
            relaxed_results = await self.api_service.search_hotels(relaxed_params)
            if relaxed_results:
                filtered_relaxed_results = self._filter_valid_results(relaxed_results)
                if filtered_relaxed_results:
                    self._log_search_results(filtered_relaxed_results)
                    # 提取旅館名稱並保存到 llm_recommend_hotel
                    hotel_names = [hotel.get("name") for hotel in filtered_relaxed_results if hotel.get("name")]
                    return {
                        "hotel_search_results": filtered_relaxed_results,
                        "search_type": "relaxed",
                        "message": "找到部分符合條件的旅館(放寬條件後搜尋)",
                        "llm_recommend_hotel": hotel_names[:3],  # 只取前三個
                    }

            # 所有搜索都失敗，返回空結果
            logger.warning("未找到符合條件的旅館")
            return {"hotel_search_results": [], "search_type": "none", "message": "未找到符合條件的旅館"}

        except Exception as e:
            logger.error(f"旅館搜索出現異常: {e}")
            return {"hotel_search_results": [], "error": str(e), "message": f"旅館搜索出現異常: {e!s}"}

    def _has_sufficient_search_conditions(self, params: dict[str, Any]) -> bool:
        """
        檢查是否有足夠的搜索條件
        """
        # 檢查是否有任何搜索條件
        if not params:
            return False

        # 檢查是否有關鍵搜索條件之一
        critical_params = ["county_ids", "district_ids", "hotel_id", "hotel_keyword"]
        has_critical_param = any(params.get(param) for param in critical_params)

        # 檢查是否有充分的參數組合
        sufficient_combinations = [
            # 縣市 + 入住日期
            (params.get("county_ids") and params.get("check_in")),
            # 縣市 + 人數
            (params.get("county_ids") and params.get("adults")),
            # 鄉鎮區 + 入住日期
            (params.get("district_ids") and params.get("check_in")),
            # 鄉鎮區 + 人數
            (params.get("district_ids") and params.get("adults")),
            # 酒店ID
            bool(params.get("hotel_id")),
            # 關鍵字
            bool(params.get("hotel_keyword")),
        ]

        # 如果任一組合成立，則認為有足夠的搜索條件
        return has_critical_param or any(sufficient_combinations)

    def _validate_required_params(self, params: dict[str, Any]) -> bool:
        """
        驗證必要參數
        """
        # 至少需要一個搜索條件
        required_params = [
            "county_id",  # 從 hotel_search_params 獲取的縣市ID
            "county_ids",  # 從狀態獲取的縣市ID列表
            "district_ids",
            "hotel_id",
            "hotel_keyword",
            "hotel_name",
            "hotel_group_types",
        ]
        has_required = any(params.get(param) for param in required_params)

        # 檢查並記錄找到的參數
        if has_required:
            found_params = [param for param in required_params if params.get(param)]
            logger.info(f"找到必要參數: {found_params}")
        else:
            logger.warning(f"缺少必要參數，參數列表: {list(params.keys())}")

        return has_required

    def _filter_api_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        篩選出適用於API的參數
        """
        # 定義API接受的參數名列表
        api_params = [
            "county_ids",
            "district_ids",
            "hotel_id",
            "hotel_keyword",
            "hotel_name",
            "hotel_group_types",
            "room_types",
            "adults",
            "children",
            "has_breakfast",
            "has_lunch",
            "has_dinner",
            "check_in",
            "check_out",
            "lowest_price",
            "highest_price",
        ]

        # 創建要返回的參數字典
        result = {}

        # 將 county_id 轉換為 county_ids
        if params.get("county_id"):
            result["county_ids"] = [params["county_id"]]

        # 複製其他API接受的參數
        for param in api_params:
            if params.get(param):
                result[param] = params[param]

        # 價格範圍處理
        if params.get("lowest_price"):
            result["lowest_price"] = params["lowest_price"]
        if params.get("highest_price"):
            result["highest_price"] = params["highest_price"]

        # 記錄最終使用的API參數
        logger.info(f"篩選後的API參數: {result}")

        return result

    def _build_search_params(self, parsed_query: dict[str, Any]) -> dict[str, Any]:
        """
        從解析後的查詢構建搜索參數
        """
        search_params = {}

        # 提取地理數據
        if "geo" in parsed_query:
            geo_data = parsed_query["geo"]
            search_params["county_ids"] = geo_data.get("county_ids", [])
            search_params["district_ids"] = geo_data.get("district_ids", [])

        # 提取日期
        if "dates" in parsed_query:
            date_data = parsed_query["dates"]
            search_params["check_in"] = date_data.get("check_in")
            search_params["check_out"] = date_data.get("check_out")

        # 提取人數
        if "guests" in parsed_query:
            guest_data = parsed_query["guests"]
            search_params["adults"] = guest_data.get("adults", 2)
            search_params["children"] = guest_data.get("children", 0)

        # 提取預算
        if "budget" in parsed_query:
            budget_data = parsed_query["budget"]
            search_params["lowest_price"] = budget_data.get("min")
            search_params["highest_price"] = budget_data.get("max")

        # 提取旅館類型
        if "hotel_type" in parsed_query:
            search_params["hotel_group_types"] = parsed_query["hotel_type"]

        # 提取關鍵字
        if "keywords" in parsed_query:
            keyword_data = parsed_query["keywords"]
            search_params["hotel_keyword"] = keyword_data.get("hotel_keyword")

        # 提取食物需求
        if "food_req" in parsed_query:
            food_data = parsed_query["food_req"]
            search_params["has_breakfast"] = food_data.get("has_breakfast", False)

        return search_params

    def _build_relaxed_search_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        構建放寬條件的搜索參數
        """
        # 複製原參數
        relaxed_params = params.copy()

        # 放寬條件的策略
        # 1. 移除價格範圍限制
        if "lowest_price" in relaxed_params:
            del relaxed_params["lowest_price"]
        if "highest_price" in relaxed_params:
            del relaxed_params["highest_price"]

        # 2. 移除設施要求
        if "hotel_facility_ids" in relaxed_params:
            del relaxed_params["hotel_facility_ids"]
        if "room_facility_ids" in relaxed_params:
            del relaxed_params["room_facility_ids"]

        # 3. 如果有縣市但沒有鄉鎮區，保留縣市
        if relaxed_params.get("county_ids") and relaxed_params.get("district_ids"):
            # 如果同時有縣市和鄉鎮區，只保留縣市範圍
            del relaxed_params["district_ids"]

        # 4. 保留人數要求，但移除其他特殊要求
        special_reqs = ["has_breakfast", "has_lunch", "has_dinner", "room_types", "bed_type"]
        for req in special_reqs:
            if req in relaxed_params:
                del relaxed_params[req]

        return relaxed_params

    def _filter_by_keyword(self, results: list, keyword: str) -> list:
        """
        使用關鍵字過濾結果
        """
        # 如果關鍵字為空或結果為空，直接返回
        if not keyword or not results:
            return results

        # 將關鍵字轉為小寫以進行不區分大小寫的比較
        keyword_lower = keyword.lower()

        # 過濾結果
        filtered_results = []
        for hotel in results:
            # 檢查旅館名稱是否包含關鍵字
            if "name" in hotel and keyword_lower in hotel["name"].lower():
                filtered_results.append(hotel)
                continue

            # 檢查旅館地址是否包含關鍵字
            if "address" in hotel and keyword_lower in hotel["address"].lower():
                filtered_results.append(hotel)
                continue

            # 檢查旅館描述是否包含關鍵字
            if "description" in hotel and hotel["description"] and keyword_lower in hotel["description"].lower():
                filtered_results.append(hotel)
                continue

        return filtered_results

    def _filter_valid_results(self, results: list) -> list:
        """
        過濾有效的結果
        """
        # 如果結果為空，直接返回
        if not results:
            return []

        # 過濾結果
        valid_results = []
        for hotel in results:
            # 檢查是否有必要的字段
            if not hotel.get("id") or not hotel.get("name"):
                continue

            # 檢查旅館名稱是否合法
            if not isinstance(hotel["name"], str) or len(hotel["name"]) < 2:
                continue

            # 如果有評分，檢查評分是否合法
            if "rating" in hotel and hotel["rating"] is not None:
                try:
                    rating = float(hotel["rating"])
                    if rating < 0 or rating > 5:
                        hotel["rating"] = None
                except (ValueError, TypeError):
                    hotel["rating"] = None

            valid_results.append(hotel)

        return valid_results

    async def _perform_relaxed_search(self, params: dict[str, Any]) -> list:
        """
        執行放寬條件的搜索
        """
        # 構建放寬條件的搜索參數
        relaxed_params = self._build_relaxed_search_params(params)

        # 執行搜索
        try:
            logger.info(f"使用放寬條件進行搜索: {relaxed_params}")
            results = await self.api_service.search_hotels(relaxed_params)
            if results:
                return self._filter_valid_results(results)
        except Exception as e:
            logger.error(f"放寬條件搜索出現異常: {e}")

        return []

    def _log_search_results(self, results: list) -> None:
        """
        記錄搜索結果
        """
        logger.info(f"找到 {len(results)} 個旅館")
        if len(results) > 0:
            hotel_names = ", ".join(hotel.get("name", "未命名") for hotel in results[:5])
            if len(results) > 5:
                hotel_names += f" 等{len(results)}家旅館"
            logger.info(f"旅館名稱預覽: {hotel_names}")


# 創建旅館搜索Agent實例
hotel_search_agent = HotelSearchAgent()
