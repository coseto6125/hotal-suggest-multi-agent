from typing import Any

from api.schemas import Hotel


class HotelAgent:
    """旅館推薦 Agent，負責搜尋和推薦旅館"""

    def __init__(self):
        # TODO: 初始化旅館推薦 Agent
        ...

    async def search_hotels(self, criteria: dict[str, Any]) -> list[Hotel]:
        """搜尋符合條件的旅館"""
        # TODO: 實現旅館搜尋邏輯

    async def get_hotel_details(self, hotel_id: str) -> Hotel:
        """獲取旅館詳細信息"""
        # TODO: 實現旅館詳情獲取邏輯
