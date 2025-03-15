"""
回應生成Agent，負責生成最終回應
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.cache.geo_cache import geo_cache


class ResponseGeneratorAgent(BaseAgent):
    """回應生成Agent"""

    def __init__(self):
        """初始化回應生成Agent"""
        super().__init__("ResponseGeneratorAgent")
        self.logger = logger

    async def process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢並生成回應"""
        return await self._process({"original_query": query, **context})

    async def _process(self, state: dict) -> dict:
        """處理生成回應的方法"""
        self.logger.info("開始生成回應")

        # 添加更詳細的日誌記錄
        self.logger.debug(f"回應生成器收到的完整輸入狀態: {str(state)[:50]}")

        # 獲取搜索結果
        hotel_search_results = state.get("hotel_search_results", [])
        fuzzy_search_results = state.get("fuzzy_search_results", [])
        plan_search_results = state.get("plan_search_results", [])

        # 記錄詳細的輸入數據類型和值
        self.logger.debug(
            f"收到的hotel_search_results類型: {type(hotel_search_results)}, 值: {str(hotel_search_results)[:30]}"
        )
        self.logger.debug(
            f"收到的fuzzy_search_results類型: {type(fuzzy_search_results)}, 值: {str(fuzzy_search_results)[:30]}"
        )
        self.logger.debug(
            f"收到的plan_search_results類型: {type(plan_search_results)}, 值: {str(plan_search_results)[:30]}"
        )

        # 合併所有搜索結果
        all_hotels = hotel_search_results + fuzzy_search_results
        self.logger.debug(
            f"合併後的all_hotels類型: {type(all_hotels)}, 長度: {len(all_hotels)}, 值: {str(all_hotels)[:30]}"
        )

        # 如果沒有找到旅館，返回無結果的回應
        if not all_hotels and not plan_search_results:
            self.logger.warning("沒有找到符合條件的旅館")
            response = {"status": "no_results", "message": "抱歉，我找不到符合您要求的旅館。請嘗試使用不同的搜索條件。"}
            return {
                **state,
                "response": response,
                "text_response": "抱歉，我找不到符合您要求的旅館。請嘗試使用不同的搜索條件，或提供更多細節，如位置、日期和預算。",
            }

        # 根據搜索結果生成回應
        query = state.get("query", "")
        self.logger.info(f"為查詢 '{query}' 生成回應，找到 {len(all_hotels)} 個旅館")

        # 生成簡短回應
        response_text = f"我找到了 {len(all_hotels)} 個符合您要求的旅館。"
        if plan_search_results:
            response_text += f" 其中 {len(plan_search_results)} 個有特別方案。"

        # 將最多3個旅館資訊添加到回應
        if all_hotels:
            response_text += "\n\n推薦旅館：\n"
            for i, hotel in enumerate(all_hotels[:3], 1):
                name = hotel.get("name", "未知旅館")
                address = hotel.get("address", "地址未提供")
                price = hotel.get("price", "價格未提供")
                response_text += f"{i}. {name} - {address}, 價格約 NT${price}\n"

        # 返回回應
        return {
            "response": {
                "status": "success",
                "hotels": all_hotels[:5],  # 限制回傳數量
                "plans": plan_search_results[:3],  # 限制回傳數量
                "message": response_text,
            },
            "text_response": response_text,
        }

    async def _enhance_geo_information(self, hotels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """使用 FAISS 向量資料庫增強旅館的地理位置資訊"""
        enhanced_hotels = []

        # 確保地理資料快取已初始化
        if not geo_cache._initialized:
            await geo_cache.initialize()

        for hotel in hotels:
            enhanced_hotel = hotel.copy()

            # 提取地址中的縣市和鄉鎮區資訊
            address = hotel.get("address", "")

            # 嘗試從地址中識別縣市
            county_info = None
            for county in await geo_cache.get_counties():
                county_name = county.get("name", "")
                if county_name and county_name in address:
                    county_info = county
                    break

            # 如果沒有直接找到，使用向量搜索
            if not county_info and address:
                # 嘗試使用地址的前幾個字符作為搜索依據
                address_prefix = address[:5]  # 取前5個字符，通常包含縣市名
                county_info = geo_cache.get_county_by_name(address_prefix)

            # 嘗試從地址中識別鄉鎮區
            district_info = None
            for district in await geo_cache.get_districts():
                district_name = district.get("name", "")
                if district_name and district_name in address:
                    district_info = district
                    break

            # 如果沒有直接找到，使用向量搜索
            if not district_info and address:
                # 嘗試使用地址的中間部分作為搜索依據
                if len(address) > 5:
                    address_middle = address[3:8]  # 取中間部分，可能包含鄉鎮區名
                    district_info = geo_cache.get_district_by_name(address_middle)

            # 添加增強的地理資訊
            if county_info:
                enhanced_hotel["county_info"] = {
                    "id": county_info.get("id"),
                    "name": county_info.get("name"),
                    "region": county_info.get("region", ""),
                }

            if district_info:
                enhanced_hotel["district_info"] = {
                    "id": district_info.get("id"),
                    "name": district_info.get("name"),
                    "county_id": district_info.get("county_id", ""),
                }

            enhanced_hotels.append(enhanced_hotel)

        return enhanced_hotels

    async def _enhance_geo_information_for_pois(self, poi_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """使用 FAISS 向量資料庫增強周邊地標的地理位置資訊"""
        enhanced_poi_results = []

        for poi_result in poi_results:
            enhanced_poi = poi_result.copy()

            # 增強景點資訊
            if "attractions" in poi_result and "places" in poi_result["attractions"]:
                enhanced_places = []
                for place in poi_result["attractions"]["places"]:
                    enhanced_place = place.copy()
                    address = place.get("formattedAddress", "")

                    # 使用向量搜索找到相關的縣市和鄉鎮區
                    if address:
                        county_info = geo_cache.get_county_by_name(address[:5])
                        if county_info:
                            enhanced_place["county_info"] = {
                                "name": county_info.get("name"),
                                "id": county_info.get("id"),
                            }

                        district_info = geo_cache.get_district_by_name(address[3:8] if len(address) > 8 else address)
                        if district_info:
                            enhanced_place["district_info"] = {
                                "name": district_info.get("name"),
                                "id": district_info.get("id"),
                            }

                    enhanced_places.append(enhanced_place)

                enhanced_poi["attractions"]["places"] = enhanced_places

            enhanced_poi_results.append(enhanced_poi)

        return enhanced_poi_results

    async def _get_region_features(self, hotels: list[dict[str, Any]]) -> str:
        """獲取旅館所在地區的特色資訊"""
        if not hotels:
            return "無地區特色資訊"

        # 從第一個旅館獲取地址
        address = hotels[0].get("address", "")
        if not address:
            return "無法獲取地區資訊"

        # 使用向量搜索找到相關的縣市
        county_info = None
        for county in await geo_cache.get_counties():
            county_name = county.get("name", "")
            if county_name and county_name in address:
                county_info = county
                break

        if not county_info:
            county_info = geo_cache.get_county_by_name(address[:5])

        if not county_info:
            return "無法識別旅館所在縣市"

        county_name = county_info.get("name", "")

        # 根據縣市提供特色資訊
        region_features = f"【{county_name}地區特色】\n"

        # 這裡可以根據不同縣市提供不同的特色資訊
        # 以下是一些示例資訊，實際應用中可以從資料庫或API獲取
        region_info = {
            "台北市": "台北市是台灣的首都，擁有豐富的美食、購物和文化景點。著名景點包括台北101、故宮博物院和饒河夜市。台北捷運系統發達，交通便利。",
            "新北市": "新北市環繞台北市，擁有豐富的自然景觀和溫泉資源。九份老街、平溪天燈和淡水漁人碼頭是熱門景點。",
            "台中市": "台中市氣候宜人，有「文化城」之稱。台中歌劇院、彩虹眷村和逢甲夜市是必訪景點。台中市以精緻咖啡廳和創意文化園區聞名。",
            "台南市": "台南市是台灣最古老的城市，擁有豐富的歷史文化遺產。赤崁樓、安平古堡和各式廟宇展現了台南的歷史風貌。台南小吃聞名全台。",
            "高雄市": "高雄是台灣南部最大城市，擁有美麗的港口和海灘。駁二藝術特區、西子灣和六合夜市是熱門景點。高雄捷運便利，適合城市觀光。",
            "基隆市": "基隆是重要的港口城市，以雨都聞名。廟口夜市提供豐富海鮮，和平島公園則展現獨特地質景觀。",
            "新竹市": "新竹市以科技產業聞名，有「風城」之稱。城隍廟夜市、新竹公園和玻璃工藝博物館是熱門景點。新竹米粉和貢丸是著名特產。",
            "嘉義市": "嘉義市是通往阿里山的門戶，文化底蘊深厚。文化路夜市、嘉義公園和森林鐵路是值得一遊的景點。",
            "宜蘭縣": "宜蘭以綠色田野和溫泉聞名，是親子旅遊的理想地點。蘭陽博物館、傳統藝術中心和礁溪溫泉是熱門景點。",
            "花蓮縣": "花蓮擁有壯麗的自然景觀，包括太魯閣國家公園和七星潭。花蓮是體驗原住民文化和戶外活動的理想地點。",
            "台東縣": "台東有美麗的海岸線和山脈，是放鬆身心的好地方。鹿野高台、池上稻田和綠島是熱門景點。",
            "澎湖縣": "澎湖是由90多個島嶼組成的群島，擁有美麗的海灘和豐富的海洋資源。澎湖是水上活動和觀光的理想地點。",
        }

        if county_name in region_info:
            region_features += region_info[county_name]
        else:
            region_features += f"{county_name}是台灣的美麗地區，擁有獨特的地方特色和風景。"

        return region_features

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

            # 添加增強的地理位置資訊
            if "county_info" in hotel:
                result += f"   所在縣市: {hotel['county_info'].get('name', '')}\n"

            if "district_info" in hotel:
                result += f"   所在鄉鎮區: {hotel['district_info'].get('name', '')}\n"

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

                    # 添加增強的地理位置資訊
                    if "county_info" in place:
                        result += f"     所在縣市: {place['county_info'].get('name', '')}\n"

                    if "district_info" in place:
                        result += f"     所在鄉鎮區: {place['district_info'].get('name', '')}\n"

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

    def _choose_search_node(self, state: dict[str, Any]) -> str:
        # 檢查是否已經嘗試過生成回應，避免循環
        if state.get("tried_response_generation"):
            logger.warning("檢測到可能的循環，強制結束工作流")
            return "search_complete"

        # 其他邏輯...

        # 當沒有足夠條件時應明確標記搜索任務為完成
        if not basic_search_ready:
            if "search_tasks_complete" not in state:
                state["search_tasks_complete"] = {}
            state["search_tasks_complete"]["hotel_search"] = True

    def _search_complete_check(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info("所有搜索任務已完成，準備生成回應")

        # 添加已嘗試生成回應的標記
        state["tried_response_generation"] = True

        return state


# 創建回應生成Agent實例
response_generator_agent = ResponseGeneratorAgent()
