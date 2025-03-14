"""
回應生成Agent，負責生成最終回應
"""

from typing import Any

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.services.llm_service import llm_service


class ResponseGeneratorAgent(BaseAgent):
    """回應生成Agent"""

    def __init__(self):
        """初始化回應生成Agent"""
        super().__init__("ResponseGeneratorAgent")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理回應生成"""
        # TODO: 實現回應生成邏輯
        original_query = inputs.get("original_query", "")
        hotels = inputs.get("hotels", [])
        hotel_details = inputs.get("hotel_details", [])
        poi_results = inputs.get("poi_results", [])

        if not original_query:
            return {"error": "原始查詢為空"}

        if not hotels:
            return {"response": "抱歉，我找不到符合您要求的旅館。請嘗試使用不同的搜索條件。"}

        logger.info(f"生成回應，旅館數量: {len(hotels)}, 周邊地標結果數量: {len(poi_results)}")

        # 構建系統提示
        system_prompt = """
        你是一個旅館推薦助手，負責為用戶提供旅館推薦和周邊探索建議。
        請根據提供的旅館信息和周邊地標信息，生成一個全面且有用的回應。
        
        回應應包括：
        1. 對用戶查詢的簡短總結
        2. 推薦的旅館列表（包括名稱、地址、價格和特點）
        3. 每個旅館周邊的景點、餐廳和交通信息
        4. 根據用戶需求提供的個性化建議
        
        請使用友好、專業的語氣，並確保信息準確、有條理。
        """

        # 構建用戶消息
        user_message = f"""
        用戶查詢: {original_query}
        
        旅館信息:
        {self._format_hotels(hotels, hotel_details)}
        
        周邊地標信息:
        {self._format_poi_results(poi_results)}
        """

        # 生成回應
        messages = [{"role": "user", "content": user_message}]
        response = await llm_service.generate_response(messages, system_prompt)

        return {"response": response}

    def _format_hotels(self, hotels: list[dict[str, Any]], hotel_details: list[dict[str, Any]]) -> str:
        """格式化旅館信息"""
        # TODO: 實現格式化旅館信息的邏輯
        if not hotels:
            return "無旅館信息"

        result = ""
        for i, hotel in enumerate(hotels[:5]):
            hotel_name = hotel.get("name", "未知")
            hotel_address = hotel.get("address", "未知")
            hotel_price = hotel.get("price", "未知")

            result += f"{i + 1}. {hotel_name}\n"
            result += f"   地址: {hotel_address}\n"
            result += f"   價格: {hotel_price} 元/晚\n"

            # 添加詳情信息（如果有）
            for detail in hotel_details:
                if detail.get("id") == hotel.get("id"):
                    hotel_description = detail.get("description", "")
                    if hotel_description:
                        result += f"   描述: {hotel_description}\n"

                    hotel_facilities = detail.get("facilities", [])
                    if hotel_facilities:
                        facilities_str = ", ".join([f.get("name", "") for f in hotel_facilities])
                        result += f"   設施: {facilities_str}\n"

                    break

            result += "\n"

        return result

    def _format_poi_results(self, poi_results: list[dict[str, Any]]) -> str:
        """格式化周邊地標信息"""
        # TODO: 實現格式化周邊地標信息的邏輯
        if not poi_results:
            return "無周邊地標信息"

        result = ""
        for poi_result in poi_results:
            hotel_name = poi_result.get("hotel_name", "未知")
            result += f"【{hotel_name}】周邊:\n"

            # 景點
            attractions = poi_result.get("attractions", {})
            places = attractions.get("places", [])
            if places:
                result += "景點:\n"
                for i, place in enumerate(places[:3]):
                    place_name = place.get("displayName", {}).get("text", "未知")
                    place_address = place.get("formattedAddress", "未知")
                    place_rating = place.get("rating", "未知")

                    result += f"  {i + 1}. {place_name}\n"
                    result += f"     地址: {place_address}\n"
                    if place_rating != "未知":
                        result += f"     評分: {place_rating}\n"

            # 餐廳
            restaurants = poi_result.get("restaurants", {})
            places = restaurants.get("places", [])
            if places:
                result += "餐廳:\n"
                for i, place in enumerate(places[:3]):
                    place_name = place.get("displayName", {}).get("text", "未知")
                    place_address = place.get("formattedAddress", "未知")
                    place_rating = place.get("rating", "未知")

                    result += f"  {i + 1}. {place_name}\n"
                    result += f"     地址: {place_address}\n"
                    if place_rating != "未知":
                        result += f"     評分: {place_rating}\n"

            # 交通
            transport = poi_result.get("transport", {})
            places = transport.get("places", [])
            if places:
                result += "交通:\n"
                for i, place in enumerate(places[:3]):
                    place_name = place.get("displayName", {}).get("text", "未知")
                    place_address = place.get("formattedAddress", "未知")

                    result += f"  {i + 1}. {place_name}\n"
                    result += f"     地址: {place_address}\n"

            result += "\n"

        return result


# 創建回應生成Agent實例
response_generator_agent = ResponseGeneratorAgent()
