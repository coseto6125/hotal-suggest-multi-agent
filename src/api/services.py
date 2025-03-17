"""
API 服務，封裝各種API調用
"""

import aiofiles
from orjson import loads

from src.api.client import api_client


class HotelAPIService:
    """旅館API服務"""

    async def get_counties(self) -> list:
        """
        獲取縣市列表
        Args:
            - page (int, optional). Defaults to 1.

        Returns:
            - List of county ids and names
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/counties"
        return await api_client.get(endpoint)

    async def get_districts(self) -> list:
        """
        獲取鄉鎮區列表
        Args:
        - page (int, optional). Defaults to 1.

        Returns:
        - List of district ids and names
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/districts"
        return await api_client.get(endpoint)

    async def get_hotel_types(self) -> list:
        """
        獲取旅館類型列表
        Args:
        - page (int, optional). Defaults to 1.

        Returns:
        - List of hotel types
        [
            {
                "type": "BASIC",
                "name": "主推"
            },
            {
                "type": "SPA",
                "name": "溫泉"
            },
            {
                "type": "PET_HOTEL",
                "name": "寵物飯店"
            },
            {
                "type": "CHECKINN",
                "name": "雀客"
            },
            {
                "type": "PARENT_CHILD_FRIENDLY",
                "name": "親子友善"
            },
            {
                "type": "SUITABLE_FOR_OFFICE",
                "name": "適合辦公室"
            }
        ]
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel_group/types"
        return await api_client.get(endpoint)

    async def get_hotel_facilities(self) -> list:
        """
        獲取飯店設施列表
        Args:
        - page (int, optional). Defaults to 1.

        Returns:
        - List of hotel facilities
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/facilities"
        return await api_client.get(endpoint)

    async def get_room_facilities(self) -> list:
        """
        獲取房間備品列表
        Args:
        - page (int, optional). Defaults to 1.

        Returns:
        - List of hotel facilities
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/room_type/facilities"
        return await api_client.get(endpoint)

    async def get_bed_types(self) -> list:
        """
        獲取房間床型列表
        Args:
        - page (int, optional). Defaults to 1.

        Returns:
        - List of hotel facilities
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/room_type/bed_types"
        return await api_client.get(endpoint)

    async def search_hotel_vacancies(self, params: dict) -> list:
        """
        搜尋可訂旅館空房
        params:
        - hotel_group_types (str): 旅館類別
        - check_in (str): 退房日期 (ex. 2025-01-01)
        - check_out (str): 退房日期 (ex. 2025-01-03)
        - adults (int): 成人數
        - children (int): 兒童數
        - lowest_price (int): 最低價格
        - highest_price (int): 最高價格
        - county_ids (int): 城市 ID 列表
        - district_ids (list): 鄉鎮區 ID 列表
        - hotel_facility_ids (list): 旅館設施 ID 列表
        - room_types (list): 房型 ID 列表
        - room_facility_ids (list): 房間設施 ID 列表
        - has_breakfast (str, int or float): 是否有早餐
        - has_lunch (str, int or float): 是否有午餐
        - has_dinner (str, int or float): 是否有晚餐
        !has 相關 API調用失敗: Invalid variable type: value
        !should be str, int or float, got True of type <class 'bool'>
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/vacancies"
        response = await api_client.get(endpoint, params)

        # 確保返回值是字典或列表
        if isinstance(response, dict):
            return response.get("data", [])
        if isinstance(response, list):
            return response
        return []

    async def search_hotel_by_supply(self, params: dict) -> list:
        """
        以關鍵字搜尋有包含某項房間備品的旅館
        Args:
        - supply_name (str): 房間備品名稱

        Returns:
        - List of hotels that contain the specified supply
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/supply"
        return await api_client.get(endpoint, params)

    async def search_plans(self, params: dict) -> list:
        """
        取得旅館訂購方案
        Args:
        - hotel_keyword (str): 旅館名稱/關鍵字
        - plan_keyword (str): 旅館訂購方案名稱/關鍵字
        - check_in_start_at (str): 退房日期 (ex. 2025-01-01)
        - check_in_end_at (str): 退房日期 (ex. 2025-01-03)

        Returns:
        - List of plans
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/plans"
        return await api_client.get(endpoint, params)

    async def fuzzy_match_hotel(self, params: dict) -> list:
        """
        取得旅館名稱模糊匹配
        Args:
        - hotel_name (str): 旅館名稱

        Returns:
        - The most similar hotel object
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/fuzzy_match"
        return await api_client.get(endpoint, params)

    async def get_hotels(self, params: dict) -> list:
        """
        取得指定類型之旅館列表
        Args:
        - hotel_group_types (str, optional). Defaults to 'basic'.

        Returns:
        - List of hotels
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotels"
        return await api_client.get(endpoint, params)

    async def get_hotel_detail(self, params: dict) -> dict:
        """
        取得旅館詳細資料
        Args:
        - hotel_name (str): 旅館名稱
        Returns:
        - The most similar hotel object
        """
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/detail"
        return await api_client.get(endpoint, params)

    async def search_hotels(self, params: dict) -> list:
        """
        搜索旅館，整合多個API調用

        Args:
            params: 搜索參數，可以包含以下字段：
                - hotel_keyword (str): 旅館名稱/關鍵字
                - county_ids (int): 城市 ID
                - district_ids (list): 鄉鎮區 ID 列表
                - check_in (str): 入住日期 (ex. 2025-01-01)
                - check_out (str): 退房日期 (ex. 2025-01-03)
                - adults (int): 成人數
                - children (int): 兒童數
                - budget_min (int): 最低價格
                - budget_max (int): 最高價格
                - hotel_facility_ids (list): 旅館設施 ID 列表
                - room_types (list): 房型 ID 列表
                - room_facility_ids (list): 房間設施 ID 列表
                - has_breakfast (str, int or float): 是否有早餐
                - has_lunch (str, int or float): 是否有午餐
                - has_dinner (str, int or float): 是否有晚餐

        Returns:
            搜索結果列表
        """
        # 構建搜索參數
        search_params = {}

        # 複製有效參數
        valid_keys = [
            "check_in",
            "check_out",
            "adults",
            "children",
            "county_ids",
            "district_ids",
            "hotel_facility_ids",
            "room_types",
            "room_facility_ids",
            "has_breakfast",
            "has_lunch",
            "has_dinner",
        ]

        for key in valid_keys:
            if key in params and params[key] is not None:
                search_params[key] = params[key]

        # 處理預算範圍
        if "budget_min" in params and params["budget_min"] is not None:
            search_params["lowest_price"] = params["budget_min"]
        if "budget_max" in params and params["budget_max"] is not None:
            search_params["highest_price"] = params["budget_max"]

        # 執行搜索
        results = await self.search_hotel_vacancies(search_params)
        
        # async with aiofiles.open("hotel_search_system/cache/new.json", encoding="utf-8") as f:
        #     results = loads(await f.read()) # ! mock data
        return results


class POIAPIService:
    """周邊地標API服務"""

    async def search_nearby_places(self, text_query: str) -> dict:
        """
        搜尋周邊地標
        Args:
        - text_query (str): 地標名稱/關鍵字
        - output_max_num (int, optional). Defaults to 5.
        - output_language (str, optional). Defaults to 'zh-TW'.
        - output_place_region (str, optional). Defaults to 'tw'.

        Returns:
        - List of nearby places
        """
        endpoint = "/api/v3/tools/external/gcp/places/nearby_search_with_query"
        data = {"text_query": text_query}
        return await api_client.post(endpoint, data)


# 創建API服務實例
hotel_api_service = HotelAPIService()
poi_api_service = POIAPIService()
