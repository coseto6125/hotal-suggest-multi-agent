from api.schemas import Place


class POIAgent:
    """周邊景點 Agent，負責搜尋和推薦周邊景點"""

    def __init__(self):
        # TODO: 初始化周邊景點 Agent
        ...

    async def search_nearby_places(self, location: dict[str, float], radius: int = 1000) -> list[Place]:
        """搜尋周邊景點"""
        # TODO: 實現周邊景點搜尋邏輯

    async def get_place_details(self, place_id: str) -> Place:
        """獲取景點詳細信息"""
        # TODO: 實現景點詳情獲取邏輯
