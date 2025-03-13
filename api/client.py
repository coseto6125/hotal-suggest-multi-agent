from config import config


class APIClient:
    """API 客戶端"""

    def __init__(self):
        # TODO: 初始化 API 客戶端
        self.base_url = config.api.base_url
        self.api_key = config.api.api_key
        self.timeout = config.api.timeout

    async def get_counties(self):
        """獲取縣市列表"""
        # TODO: 實現縣市列表獲取邏輯

    async def get_districts(self, county_id: str):
        """獲取鄉鎮區列表"""
        # TODO: 實現鄉鎮區列表獲取邏輯

    async def search_hotels(self, params: dict):
        """搜尋旅館"""
        # TODO: 實現旅館搜尋邏輯

    async def get_nearby_places(self, params: dict):
        """搜尋周邊景點"""
        # TODO: 實現周邊景點搜尋邏輯
