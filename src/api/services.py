"""
API 服務，封裝各種API調用
"""

from src.api.client import api_client


class HotelAPIService:
    """旅館API服務"""

    async def get_counties(self) -> list:
        """獲取縣市列表"""
        # TODO: 實現獲取縣市列表的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/counties"
        return await api_client.get(endpoint)

    async def get_districts(self, county_id: str | None = None) -> list:
        """獲取鄉鎮區列表"""
        # TODO: 實現獲取鄉鎮區列表的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/districts"
        params = {"county_id": county_id} if county_id else None
        return await api_client.get(endpoint, params)

    async def get_hotel_types(self) -> list:
        """獲取旅館類型列表"""
        # TODO: 實現獲取旅館類型列表的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel_group/types"
        return await api_client.get(endpoint)

    async def get_hotel_facilities(self) -> list:
        """獲取飯店設施列表"""
        # TODO: 實現獲取飯店設施列表的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/facilities"
        return await api_client.get(endpoint)

    async def get_room_facilities(self) -> list:
        """獲取房間備品列表"""
        # TODO: 實現獲取房間備品列表的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/room_type/facilities"
        return await api_client.get(endpoint)

    async def get_bed_types(self) -> list:
        """獲取房間床型列表"""
        # TODO: 實現獲取房間床型列表的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/room_type/bed_types"
        return await api_client.get(endpoint)

    async def search_hotel_vacancies(self, params: dict) -> list:
        """搜尋可訂旅館空房"""
        # TODO: 實現搜尋可訂旅館空房的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/vacancies"
        return await api_client.get(endpoint, params)

    async def search_hotel_by_supply(self, params: dict) -> list:
        """根據備品搜尋旅館"""
        # TODO: 實現根據備品搜尋旅館的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/supply"
        return await api_client.get(endpoint, params)

    async def search_plans(self, params: dict) -> list:
        """搜尋可用訂購方案"""
        # TODO: 實現搜尋可用訂購方案的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/plans"
        return await api_client.get(endpoint, params)

    async def fuzzy_match_hotel(self, name: str) -> list:
        """模糊比對旅館名稱"""
        # TODO: 實現模糊比對旅館名稱的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/fuzzy_match"
        params = {"name": name}
        return await api_client.get(endpoint, params)

    async def get_hotels(self, params: dict) -> list:
        """獲取指定類別旅館"""
        # TODO: 實現獲取指定類別旅館的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotels"
        return await api_client.get(endpoint, params)

    async def get_hotel_detail(self, hotel_id: str) -> dict:
        """獲取旅館詳情"""
        # TODO: 實現獲取旅館詳情的API調用
        endpoint = "/api/v3/tools/interview_test/taiwan_hotels/hotel/detail"
        params = {"hotel_id": hotel_id}
        return await api_client.get(endpoint, params)


class POIAPIService:
    """周邊地標API服務"""

    async def search_nearby_places(self, text_query: str) -> dict:
        """搜尋周邊地標"""
        # TODO: 實現搜尋周邊地標的API調用
        endpoint = "/api/v3/tools/external/gcp/places/nearby_search_with_query"
        data = {"text_query": text_query}
        return await api_client.post(endpoint, data)


# 創建API服務實例
hotel_api_service = HotelAPIService()
poi_api_service = POIAPIService()
