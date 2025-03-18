"""
回應生成Agent，負責生成最終回應
"""

from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent
from src.cache.geo_cache import geo_cache
from src.web.websocket import ws_manager


class ResponseGeneratorAgent(BaseAgent):
    """回應生成Agent - 負責處理和清洗旅館數據，並將其發送給前端"""

    def __init__(self):
        """初始化回應生成Agent"""
        super().__init__("ResponseGeneratorAgent")
        self.logger = logger

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理生成回應的方法 - 清洗數據並準備回應"""
        self.logger.info("開始清洗和整理旅館數據")

        # 添加更詳細的日誌記錄
        self.logger.debug(f"回應生成器收到的完整輸入狀態: {str(state)[:50]}")

        # 獲取搜索結果
        hotel_search_results = state.get("hotel_search_results", [])
        fuzzy_search_results = state.get("fuzzy_search_results", [])
        plan_search_results = state.get("plan_search_results", [])
        session_id = state.get("session_id", "")

        # 記錄詳細的輸入數據類型和值
        self.logger.debug(f"收到的hotel_search_results: {len(hotel_search_results)}間 旅館資料")
        self.logger.debug(f"收到的fuzzy_search_results: {len(fuzzy_search_results)}間 旅館資料")
        self.logger.debug(f"收到的plan_search_results: {len(plan_search_results)}間 旅館資料")

        # 合併所有搜索結果
        all_hotels = hotel_search_results + fuzzy_search_results
        self.logger.debug(
            f"合併後的all_hotels類型: {type(all_hotels)}, 長度: {len(all_hotels)}, 值: {str(all_hotels)[:30]}"
        )

        # 如果沒有找到旅館，返回無結果的回應
        if not all_hotels and not plan_search_results:
            self.logger.warning("沒有找到符合條件的旅館")
            # 僅設置狀態，不直接發送消息給前端（因為 LLM 已經會處理回應）
            response = {"status": "no_results", "message": ""}

            # 不再向前端發送消息
            # if session_id:
            #     await ws_manager.broadcast_chat_message(
            #         session_id,
            #         {
            #             "role": "assistant",
            #             "content": "抱歉，我找不到符合您要求的旅館。請嘗試使用不同的搜索條件，或提供更多細節，如位置、日期和預算。",
            #             "timestamp": "",
            #         },
            #     )

            return {
                **state,
                "response": response,
                "text_response": " 抱歉，我找不到符合您要求的旅館。請嘗試使用不同的搜索條件，或提供更多細節，如位置、日期和預算。",
                "clean_hotels": [],
                "clean_plans": [],
                "hotel_details": [],
                "plan_details": [],
            }

        # 根據搜索結果準備回應
        query = state.get("query", "")
        self.logger.info(f"為查詢 '{query}' 整理數據，找到 {len(all_hotels)} 個旅館")

        # 清洗和整理旅館資料 - 將旅館資料和方案資料合併為一個字串
        hotels_text = self._format_hotels_for_llm(all_hotels)
        plans_text = self._format_plans_for_llm(plan_search_results)

        # 合併為一個完整的字串
        hotel_details = hotels_text + plans_text

        # 為前端準備旅館和方案資料
        clean_hotels = await self._prepare_frontend_hotels(all_hotels)
        clean_plans = await self._prepare_frontend_plans(plan_search_results)

        # 準備簡短回應
        response_text = f"我找到了 {len(clean_hotels)} 個符合您要求的旅館。"
        if clean_plans:
            response_text += f" 其中 {len(clean_plans)} 個有特別方案。"

        # 通過WebSocket發送清洗後的旅館資料
        if session_id:
            await self._send_hotels_to_frontend(session_id, clean_hotels, clean_plans)

        # 返回清洗後的資料
        return {
            **state,
            "response": {
                "status": "success",
                "hotels": hotel_details,
                "message": response_text,
            },
            "text_response": response_text,
            "clean_hotels": clean_hotels,
            "clean_plans": clean_plans,
            "hotel_details": hotel_details,
        }

    async def _clean_hotel_data(self, hotels: list[dict[str, Any]]) -> list[str]:
        """清洗和整理旅館資料，返回適合LLM評估的字串列表"""
        self.logger.info(f"開始清洗 {len(hotels)} 間旅館資料")
        clean_hotels_data = []
        hotel_details_list = []

        # 確保地理資料快取已初始化
        if not geo_cache._initialized:
            await geo_cache.initialize()

        # 處理每個旅館
        for i, hotel in enumerate(hotels[:10]):  # 限制處理數量
            # 創建詳細的基本資料
            clean_hotel = {
                "id": hotel.get("id", ""),
                "name": hotel.get("name", "未知"),
                "address": hotel.get("address", "未知"),
                "price": self._format_price(hotel.get("price")),
                "rating": hotel.get("rating", 0),
                "rating_text": self._convert_rating_to_text(hotel.get("rating", 0)),
                "intro": hotel.get("intro", ""),
                "intro_summary": self._summarize_text(hotel.get("intro", ""), 150),
                "check_in": self._format_time(hotel.get("check_in", "")),
                "check_out": self._format_time(hotel.get("check_out", "")),
                "last_check_in": self._format_time(hotel.get("last_check_in", "")),
                "phone": self._format_phone(hotel.get("phone", "")),
                "image_url": hotel.get("image_url", ""),
                "url": hotel.get("url", ""),
                "location": {
                    "latitude": hotel.get("latitude", 0),
                    "longitude": hotel.get("longitude", 0),
                },
                "meals": self._format_meals(hotel.get("meals")),
                "booking_notice": self._format_booking_notice(hotel.get("booking_notice", "")),
            }

            # 處理地理位置資訊
            clean_hotel["location_info"] = self._extract_location_info(hotel)

            # 處理設施資訊
            facilities = hotel.get("facilities", [])
            if facilities:
                popular_facilities = [f.get("name", "") for f in facilities if f.get("is_popular", True)]
                other_facilities = [f.get("name", "") for f in facilities if not f.get("is_popular", False)]

                clean_hotel["facilities"] = {
                    "popular": popular_facilities,
                    "all": [f.get("name", "") for f in facilities],
                    "others": other_facilities,
                }

                # 將設施分類
                facility_categories = self._categorize_facilities(facilities)
                clean_hotel["facility_categories"] = facility_categories

            # 處理房型資訊
            room_types = hotel.get("suitable_room_types", [])
            if room_types:
                clean_hotel["room_types"] = self._extract_room_types(room_types)

            # 處理取消政策
            cancel_policies = hotel.get("cancel_policies", [])
            if cancel_policies:
                clean_hotel["cancel_policies"] = self._format_cancel_policies(cancel_policies)

            clean_hotels_data.append(clean_hotel)

            # 為LLM創建文本格式的旅館詳情
            hotel_detail = self._format_hotel_for_llm(i + 1, clean_hotel)
            hotel_details_list.append(hotel_detail)

        self.logger.info(f"完成清洗 {len(clean_hotels_data)} 間旅館資料")
        return hotel_details_list  # 返回文本格式的旅館詳情列表

    def _format_hotel_for_llm(self, index: int, hotel: dict[str, Any]) -> str:
        """將旅館資料格式化為LLM易於理解的文本"""
        name = hotel.get("name", "未知")
        address = hotel.get("address", "未知")

        # 獲取縣市區域資訊
        location_info = hotel.get("location_info", {})
        county = location_info.get("county", {})
        county_name = county.get("name", "") if isinstance(county, dict) else county

        district = location_info.get("district", {})
        district_name = district.get("name", "") if isinstance(district, dict) else district

        location_text = (
            f"{county_name}{district_name}" if county_name and district_name else (county_name or district_name or "")
        )

        # 旅館基本資訊
        result_lines = []
        result_lines.append(f"【旅館{index}】{name}\n")
        result_lines.append(f"地址: {address}\n")
        if location_text:
            result_lines.append(f"位置: {location_text}\n")

        result_lines.append(f"價格: {hotel.get('price', '未提供')}\n")

        if hotel.get("rating_text"):
            result_lines.append(f"評價: {hotel.get('rating_text', '')}\n")

        # 入住退房資訊
        check_in = hotel.get("check_in", "")
        check_out = hotel.get("check_out", "")
        if check_in and check_out:
            result_lines.append(f"入住: {check_in}, 退房: {check_out}\n")

        # 設施資訊
        if "facilities" in hotel and "popular" in hotel["facilities"] and hotel["facilities"]["popular"]:
            popular = hotel["facilities"]["popular"][:5]  # 限制數量
            result_lines.append(f"主要設施: {', '.join(popular)}\n")

        # 房型資訊
        if hotel.get("room_types"):
            result_lines.append("客房類型:\n")
            for j, room in enumerate(hotel["room_types"][:2]):  # 限制顯示的房型數量
                result_lines.append(
                    f"  - {room.get('name', '')}: {room.get('price', '')}, 可住{room.get('capacity', {}).get('total', 0)}人\n"
                )

        # 旅館簡介
        if hotel.get("intro_summary"):
            result_lines.append(f"簡介: {hotel.get('intro_summary', '')}\n")

        # 取消政策
        if hotel.get("cancel_policies"):
            for policy in hotel["cancel_policies"][:1]:  # 只顯示最重要的取消政策
                result_lines.append(f"取消政策: {policy.get('period', '')}{policy.get('description', '')}\n")

        return "".join(result_lines)

    def _extract_location_info(self, hotel: dict[str, Any]) -> dict[str, Any]:
        """從旅館資料中提取地理位置信息"""
        location_info = {}

        # 縣市資訊
        if hotel.get("county"):
            location_info["county"] = hotel["county"]
        elif hotel.get("county_info"):
            location_info["county"] = hotel["county_info"]

        # 區域資訊
        if hotel.get("district"):
            location_info["district"] = hotel["district"]
        elif hotel.get("district_info"):
            location_info["district"] = hotel["district_info"]

        # 國家、省份資訊
        if hotel.get("country"):
            location_info["country"] = hotel["country"]
        if hotel.get("province"):
            location_info["province"] = hotel["province"]

        # 提取地址中的郵遞區號和詳細地址
        address = hotel.get("address", "")
        if address:
            postal_code = self._extract_postal_code(address)
            if postal_code:
                location_info["postal_code"] = postal_code

            # 提取英文地址和中文地址
            address_parts = address.split(" ", 1)
            if len(address_parts) > 1 and any(c.isascii() for c in address_parts[1]):
                location_info["zh_address"] = address_parts[0]
                location_info["en_address"] = address_parts[1]
            else:
                location_info["full_address"] = address

        return location_info

    def _extract_postal_code(self, address: str) -> str:
        """從地址中提取郵遞區號"""
        # 台灣郵遞區號通常為3-5位數字
        import re

        match = re.match(r"^\d{3,5}", address)
        return match.group(0) if match else ""

    def _extract_room_types(self, room_types: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """提取並格式化房型資訊"""
        formatted_room_types = []

        for room in room_types:
            formatted_room = {
                "id": room.get("id", ""),
                "name": room.get("name", "未知房型"),
                "price": self._format_price(room.get("price")),
                "area": f"{room.get('avg_square_feet', 0)}坪" if room.get("avg_square_feet") else "未提供",
                "bed_type": room.get("bed_type", "未提供"),
                "capacity": {
                    "adults": room.get("adults", 0),
                    "children": room.get("children", 0),
                    "total": room.get("adults", 0) + room.get("children", 0),
                },
                "intro": room.get("intro", ""),
                "intro_summary": self._summarize_text(room.get("intro", ""), 100),
            }

            # 處理房型設施
            if room.get("facilities"):
                formatted_room["facilities"] = [f.get("name", "") for f in room["facilities"]]

            # 處理價格方案
            if room.get("prices"):
                price_plans = []
                for price_data in room["prices"]:
                    plan = {
                        "date": price_data.get("date", ""),
                        "price": self._format_price(price_data.get("price")),
                        "availability": price_data.get("rooms", 0),
                    }
                    if price_data.get("plan"):
                        plan["plan_name"] = price_data["plan"].get("name", "基本方案")
                        if "keywords" in price_data["plan"] and price_data["plan"]["keywords"]:
                            plan["keywords"] = price_data["plan"]["keywords"]
                    price_plans.append(plan)
                formatted_room["price_plans"] = price_plans

            formatted_room_types.append(formatted_room)

        return formatted_room_types

    def _format_cancel_policies(self, policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """格式化取消政策為更易讀的格式"""
        formatted_policies = []

        for policy in policies:
            formatted_policy = {
                "description": policy.get("description", ""),
                "refund_percent": 100 - policy.get("percent", 0),
            }

            # 格式化時間段
            start_days = policy.get("start_days")
            end_days = policy.get("end_days")

            if start_days is None and end_days is not None:
                formatted_policy["period"] = f"入住前{end_days}天及更早"
            elif start_days is not None and end_days is not None:
                if start_days == end_days:
                    formatted_policy["period"] = f"入住前{start_days}天"
                else:
                    formatted_policy["period"] = f"入住前{start_days}-{end_days}天"
            elif start_days == 0 and end_days == 0:
                formatted_policy["period"] = "入住當天或入住後"

            formatted_policies.append(formatted_policy)

        return formatted_policies

    def _categorize_facilities(self, facilities: list[dict[str, Any]]) -> dict[str, list[str]]:
        """將設施分類為不同類別"""
        categories = {
            "安全設施": [],
            "服務設施": [],
            "客房設施": [],
            "交通設施": [],
            "餐飲設施": [],
            "清潔與健康": [],
            "語言服務": [],
            "支付選項": [],
            "其他設施": [],
        }

        for facility in facilities:
            name = facility.get("name", "")
            if not name:
                continue

            if any(keyword in name for keyword in ["消毒", "清潔", "體溫", "口罩", "衛生"]):
                categories["清潔與健康"].append(name)
            elif any(keyword in name for keyword in ["急救", "滅火", "監視", "AED", "煙霧"]):
                categories["安全設施"].append(name)
            elif any(keyword in name for keyword in ["櫃檯", "接待", "入住", "行李", "退房", "收取包裹", "外送"]):
                categories["服務設施"].append(name)
            elif any(keyword in name for keyword in ["停車", "接送", "交通"]):
                categories["交通設施"].append(name)
            elif any(keyword in name for keyword in ["中文", "英文", "日文", "韓文"]):
                categories["語言服務"].append(name)
            elif any(keyword in name for keyword in ["刷卡", "支付", "電子支付"]):
                categories["支付選項"].append(name)
            elif any(keyword in name for keyword in ["早餐", "餐廳", "咖啡", "茶"]):
                categories["餐飲設施"].append(name)
            else:
                categories["其他設施"].append(name)

        # 刪除空類別
        return {k: v for k, v in categories.items() if v}

    def _format_meals(self, meals) -> str:
        """格式化餐食資訊"""
        if not meals:
            return "不提供餐食"

        if isinstance(meals, list):
            try:
                meal_mapping = {1: "早餐", 2: "中餐", 3: "晚餐"}
                formatted_meals = []
                for meal in meals:
                    if isinstance(meal, int) and meal in meal_mapping:
                        formatted_meals.append(meal_mapping[meal])
                    else:
                        # 確保所有非整數型別的餐食都轉為字串
                        formatted_meals.append(str(meal))

                # 確保所有列表項都是字串，再進行join操作
                return ", ".join(formatted_meals)
            except Exception as e:
                self.logger.error(f"餐食資訊格式化錯誤: {e}, 原始資料: {meals}")
                return "有提供餐食，但需要洽詢"

        # 非列表類型，直接轉為字串
        return str(meals)

    def _format_booking_notice(self, notice: str) -> list[str]:
        """將預訂須知分拆為條文列表"""
        if not notice:
            return []

        # 根據段落或數字標記分拆
        import re

        # 先按行分拆
        lines = notice.split("\n")

        # 整理成條文，合併不是以數字或特殊符號開頭的行
        formatted_lines = []
        current_line = ""

        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue

            # 檢查是否是新條目開始
            if re.match(r"^[0-9\.\-►•]+", clean_line) or "【" in clean_line[:3]:
                if current_line:
                    formatted_lines.append(current_line)
                current_line = clean_line
            else:
                current_line += " " + clean_line

        # 添加最後一行
        if current_line:
            formatted_lines.append(current_line)

        return formatted_lines

    def _format_time(self, time_str: str) -> str:
        """格式化時間"""
        if not time_str:
            return ""

        # 處理24小時制時間
        if ":" in time_str:
            try:
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = parts[1][:2]

                # 轉為易讀格式
                if hour < 12:
                    return f"上午{hour}:{minute}"
                if hour == 12:
                    return f"中午{hour}:{minute}"
                return f"下午{hour - 12}:{minute}"
            except (ValueError, IndexError):
                return time_str

        return time_str

    def _format_phone(self, phone: str) -> str:
        """格式化電話號碼"""
        if not phone:
            return ""

        # 統一格式，去除空格
        phone = phone.replace(" ", "")

        # 格式化台灣電話號碼
        if phone.startswith("0"):
            if len(phone) == 10:  # 行動電話
                return f"{phone[:4]}-{phone[4:7]}-{phone[7:]}"
            if len(phone) == 9:  # 市話
                return f"{phone[:2]}-{phone[2:5]}-{phone[5:]}"

        return phone

    def _format_price(self, price) -> str:
        """格式化價格"""
        if not price:
            return "未提供"

        try:
            price_int = int(float(price))
            return f"NT$ {price_int:,}"
        except (ValueError, TypeError):
            return str(price)

    def _convert_rating_to_text(self, rating: float) -> str:
        """將數字評分轉換為文字描述"""
        if not rating:
            return "尚無評價"

        rating = float(rating)
        if rating >= 4.5:
            return "極佳"
        if rating >= 4.0:
            return "非常好"
        if rating >= 3.5:
            return "好"
        if rating >= 3.0:
            return "滿意"
        return "普通"

    def _summarize_text(self, text: str, max_length: int = 100) -> str:
        """簡化長文本"""
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        # 嘗試在句號、問號或感嘆號處截斷
        for i in range(max_length, max(max_length - 30, 0), -1):
            if i < len(text) and text[i] in ["。", "!", "?", "！", "？", "."]:
                return text[: i + 1]

        # 如果找不到合適的截斷點，直接截斷並加上省略號
        return text[:max_length] + "..."

    async def _clean_plan_data(self, plans: list[dict[str, Any]]) -> list[str]:
        """清洗和整理方案資料，返回適合LLM評估的字串列表"""
        if not plans:
            return []

        self.logger.info(f"開始清洗 {len(plans)} 個方案資料")
        clean_plans_data = []
        plan_details_list = []

        for i, plan in enumerate(plans[:5]):  # 限制回傳數量
            clean_plan = {
                "id": plan.get("plan_id", ""),
                "name": plan.get("plan_name", "未知方案"),
                "hotel_id": plan.get("hotel_id", ""),
                "hotel_name": plan.get("hotel_name", "未知旅館"),
                "price": self._format_price(plan.get("price", 0)),
                "original_price": self._format_price(plan.get("original_price"))
                if plan.get("original_price")
                else None,
                "discount_percent": self._calculate_discount(plan.get("price", 0), plan.get("original_price"))
                if plan.get("original_price")
                else None,
                "description": plan.get("description", ""),
                "description_summary": self._summarize_text(plan.get("description", ""), 120),
                "image_url": plan.get("image_url", ""),
                "url": plan.get("url", ""),
                "date_range": self._format_date_range(plan.get("start_date"), plan.get("end_date")),
                "valid_days": self._count_valid_days(plan.get("start_date"), plan.get("end_date")),
            }

            # 整理方案條款
            if plan.get("terms"):
                clean_plan["terms"] = self._format_plan_terms(plan["terms"])

            # 整理適用房型
            if plan.get("room_types"):
                clean_plan["room_types"] = [
                    {"name": room.get("name", "未知房型"), "id": room.get("id")} for room in plan["room_types"]
                ]

            clean_plans_data.append(clean_plan)

            # 為LLM創建文本格式的方案詳情
            plan_detail = self._format_plan_for_llm(i + 1, clean_plan)
            plan_details_list.append(plan_detail)

        self.logger.info(f"完成清洗 {len(clean_plans_data)} 個方案資料")
        return plan_details_list  # 返回文本格式的方案詳情列表

    def _calculate_discount(self, current: float, original: float) -> str:
        """計算折扣百分比"""
        try:
            current = float(current)
            original = float(original)
            if original > 0:
                discount = (original - current) / original * 100
                return f"{discount:.0f}%"
        except (ValueError, TypeError):
            pass
        return None

    def _format_date_range(self, start_date: str, end_date: str) -> str:
        """格式化日期範圍"""
        if not start_date and not end_date:
            return "不限日期"
        if start_date and not end_date:
            return f"{start_date} 起"
        if not start_date and end_date:
            return f"至 {end_date}"
        return f"{start_date} ~ {end_date}"

    def _count_valid_days(self, start_date: str, end_date: str) -> int:
        """計算有效天數"""
        if not start_date or not end_date:
            return 0

        try:
            from datetime import datetime

            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            return (end - start).days + 1
        except (ValueError, TypeError):
            return 0

    def _format_plan_terms(self, terms: list[str] or str) -> list[str]:
        """格式化方案條款"""
        if not terms:
            return []

        if isinstance(terms, str):
            # 按行分拆
            return [line.strip() for line in terms.split("\n") if line.strip()]

        if isinstance(terms, list):
            return terms

        return []

    def _format_plan_for_llm(self, index: int, plan: dict[str, Any]) -> str:
        """將方案資料格式化為LLM易於理解的文本"""
        name = plan.get("name", "未知方案")
        hotel_name = plan.get("hotel_name", "")

        result_lines = []
        result_lines.append(f"【方案{index}】{name} ({hotel_name})\n")
        result_lines.append(f"價格: {plan.get('price', '')}")

        if plan.get("discount_percent"):
            result_lines.append(f" (折扣: {plan.get('discount_percent', '')})")

        result_lines.append("\n")

        if plan.get("date_range"):
            result_lines.append(f"有效期間: {plan.get('date_range', '')}\n")

        if plan.get("description_summary"):
            result_lines.append(f"內容: {plan.get('description_summary', '')}\n")

        # 添加方案條款
        if plan.get("terms") and isinstance(plan["terms"], list) and plan["terms"]:
            result_lines.append("條款:\n")
            for term in plan["terms"][:3]:  # 限制顯示的條款數量
                result_lines.append(f"  - {term}\n")

        # 添加適用房型
        if plan.get("room_types") and isinstance(plan["room_types"], list) and plan["room_types"]:
            result_lines.append("適用房型:\n")
            for room in plan["room_types"][:2]:  # 限制顯示的房型數量
                result_lines.append(f"  - {room.get('name', '')}\n")

        return "".join(result_lines)

    async def _send_hotels_to_frontend(
        self, session_id: str, hotels: list[dict[str, Any]], plans: list[dict[str, Any]]
    ) -> None:
        """將旅館和方案資料通過WebSocket發送給前端"""
        try:
            # 準備旅館資料
            frontend_hotels = []
            if hotels:
                # 簡化給前端的資料，避免過大
                for hotel in hotels:
                    frontend_hotel = {
                        "id": hotel.get("id", ""),
                        "name": hotel.get("name", ""),
                        "address": hotel.get("address", ""),
                        "price": hotel.get("price", ""),
                        "rating_text": hotel.get("rating_text", ""),
                        "intro_summary": hotel.get("intro_summary", ""),
                        "check_in": hotel.get("check_in", ""),
                        "check_out": hotel.get("check_out", ""),
                        "image_url": hotel.get("image_url", ""),
                        "phone": hotel.get("phone", ""),
                        "url": hotel.get("url", ""),
                    }

                    # 添加主要設施
                    if "facilities" in hotel and "popular" in hotel["facilities"]:
                        try:
                            # 確保設施是字串列表
                            frontend_hotel["facilities"] = [str(f) for f in hotel["facilities"]["popular"][:5]]
                        except Exception as e:
                            self.logger.error(f"處理設施時發生錯誤: {e}")
                            frontend_hotel["facilities"] = []

                    # 添加地理位置
                    if "location_info" in hotel:
                        try:
                            location = hotel["location_info"]
                            county = location.get("county", "")
                            district = location.get("district", "")

                            # 處理不同數據結構
                            county_name = county.get("name", "") if isinstance(county, dict) else str(county)
                            district_name = district.get("name", "") if isinstance(district, dict) else str(district)

                            frontend_hotel["location"] = {"county": county_name, "district": district_name}
                        except Exception as e:
                            self.logger.error(f"處理地理位置時發生錯誤: {e}")
                            frontend_hotel["location"] = {"county": "", "district": ""}

                    frontend_hotels.append(frontend_hotel)

            # 準備方案資料
            frontend_plans = []
            if plans:
                # 簡化給前端的資料
                for plan in plans:
                    try:
                        frontend_plan = {
                            "id": plan.get("id", ""),
                            "name": str(plan.get("name", "")),
                            "hotel_name": str(plan.get("hotel_name", "")),
                            "price": str(plan.get("price", "")),
                            "discount_percent": str(plan.get("discount_percent", "")),
                            "description_summary": str(plan.get("description_summary", "")),
                            "image_url": plan.get("image_url", ""),
                            "url": plan.get("url", ""),
                            "date_range": str(plan.get("date_range", "")),
                        }
                        frontend_plans.append(frontend_plan)
                    except Exception as e:
                        self.logger.error(f"處理方案資料時發生錯誤: {e}")

            # 準備綜合回應訊息
            response_text = f"我找到了 {len(hotels)} 個符合您要求的旅館"
            if plans:
                response_text += f"，其中 {len(plans)} 個有特別方案"
            response_text += "。"

            # 發送綜合訊息
            combined_message = {
                "role": "assistant",
                "content": response_text,
                "hotels": frontend_hotels,
                "plans": frontend_plans,
                "timestamp": "",
            }

            self.logger.debug(f"正在發送綜合資料到前端: {len(frontend_hotels)} 間旅館和 {len(frontend_plans)} 個方案")
            await ws_manager.broadcast_chat_message(session_id, combined_message)
            self.logger.info(f"已發送綜合資料到前端: {len(frontend_hotels)} 間旅館和 {len(frontend_plans)} 個方案")

        except Exception as e:
            self.logger.error(f"發送資料到前端失敗: {e}")
            # 嘗試發送簡單文本消息通知用戶
            try:
                await ws_manager.broadcast_chat_message(
                    session_id,
                    {
                        "role": "system",
                        "content": f"找到 {len(hotels)} 間旅館和 {len(plans)} 個方案，但無法完整顯示資料。請重試或聯絡客服。",
                        "timestamp": "",
                    },
                )
            except Exception as e2:
                self.logger.error(f"發送錯誤通知也失敗: {e2}")

    async def _prepare_frontend_hotels(self, hotels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """準備前端顯示用的旅館資料"""
        self.logger.info(f"開始準備前端顯示用的旅館資料，共 {len(hotels)} 間")
        clean_hotels = []

        # 確保地理資料快取已初始化
        if not geo_cache._initialized:
            await geo_cache.initialize()

        # 處理每個旅館
        for hotel in hotels[:10]:  # 限制處理數量
            # 創建詳細的基本資料
            clean_hotel = {
                "id": hotel.get("id", ""),
                "name": hotel.get("name", "未知"),
                "address": hotel.get("address", "未知"),
                "price": self._format_price(hotel.get("price")),
                "rating": hotel.get("rating", 0),
                "rating_text": self._convert_rating_to_text(hotel.get("rating", 0)),
                "intro_summary": self._summarize_text(hotel.get("intro", ""), 150),
                "check_in": self._format_time(hotel.get("check_in", "")),
                "check_out": self._format_time(hotel.get("check_out", "")),
                "phone": self._format_phone(hotel.get("phone", "")),
                "image_url": hotel.get("image_url", ""),
                "url": hotel.get("url", ""),
            }

            # 處理地理位置資訊
            location_info = self._extract_location_info(hotel)
            county = location_info.get("county", "")
            district = location_info.get("district", "")

            # 處理不同數據結構
            county_name = county.get("name", "") if isinstance(county, dict) else str(county)
            district_name = district.get("name", "") if isinstance(district, dict) else str(district)

            clean_hotel["location"] = {"county": county_name, "district": district_name}

            # 處理設施資訊
            facilities = hotel.get("facilities", [])
            if facilities:
                popular_facilities = [f.get("name", "") for f in facilities if f.get("is_popular", True)]
                clean_hotel["facilities"] = popular_facilities[:5]  # 只取前5個主要設施

            clean_hotels.append(clean_hotel)

        self.logger.info(f"完成準備前端顯示用的旅館資料，共 {len(clean_hotels)} 間")
        return clean_hotels

    async def _prepare_frontend_plans(self, plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """準備前端顯示用的方案資料"""
        if not plans:
            return []

        self.logger.info(f"開始準備前端顯示用的方案資料，共 {len(plans)} 個")
        clean_plans = []

        for plan in plans[:5]:  # 限制回傳數量
            clean_plan = {
                "id": plan.get("plan_id", ""),
                "name": plan.get("plan_name", "未知方案"),
                "hotel_name": plan.get("hotel_name", "未知旅館"),
                "price": self._format_price(plan.get("price", 0)),
                "discount_percent": self._calculate_discount(plan.get("price", 0), plan.get("original_price")),
                "description_summary": self._summarize_text(plan.get("description", ""), 120),
                "image_url": plan.get("image_url", ""),
                "url": plan.get("url", ""),
                "date_range": self._format_date_range(plan.get("start_date"), plan.get("end_date")),
            }

            clean_plans.append(clean_plan)

        self.logger.info(f"完成準備前端顯示用的方案資料，共 {len(clean_plans)} 個")
        return clean_plans

    def _format_hotels_for_llm(self, hotels: list[dict[str, Any]]) -> str:
        """將旅館資料格式化為LLM易於理解的文本"""
        if not hotels:
            return "無旅館資料"

        result_lines = []
        result_lines.append("旅館資料\n\n")

        # 限制處理的旅館數量，避免超出LLM上下文長度
        max_hotels = min(10, len(hotels))

        for i, hotel in enumerate(hotels[:max_hotels]):
            name = hotel.get("name", "未知")
            address = hotel.get("address", "未知")
            price = hotel.get("price", "未提供")
            rating = hotel.get("rating_text", "")

            # 獲取縣市區域資訊
            location_info = hotel.get("location_info", {})
            county = location_info.get("county", {})
            county_name = county.get("name", "") if isinstance(county, dict) else county

            district = location_info.get("district", {})
            district_name = district.get("name", "") if isinstance(district, dict) else district

            location_text = (
                f"{county_name}{district_name}"
                if county_name and district_name
                else (county_name or district_name or "")
            )

            # 旅館基本資訊 - 使用更簡潔的格式
            result_lines.append(f"旅館{i + 1}: {name}\n")
            result_lines.append(f"地址: {address}\n")
            if location_text:
                result_lines.append(f"位置: {location_text}\n")
            result_lines.append(f"價格: {price}\n")
            if rating:
                result_lines.append(f"評價: {rating}\n")

            # 入住退房資訊
            check_in = hotel.get("check_in", "")
            check_out = hotel.get("check_out", "")
            if check_in and check_out:
                result_lines.append(f"入住/退房: {check_in} / {check_out}\n")

            # 設施資訊 - 使用簡潔的清單格式
            facilities = hotel.get("facilities", [])
            if facilities:
                popular_facilities = [f.get("name", "") for f in facilities if f.get("is_popular", True)]
                if popular_facilities:
                    result_lines.append("主要設施: ")
                    result_lines.append(", ".join(popular_facilities[:5]))  # 限制顯示的設施數量
                    result_lines.append("\n")

            # 房型資訊 - 使用簡潔的清單格式
            room_types = hotel.get("suitable_room_types", [])
            if room_types:
                result_lines.append("客房類型:\n")
                for j, room in enumerate(room_types[:3]):  # 限制顯示的房型數量
                    room_name = room.get("name", "")
                    room_price = room.get("price", "")
                    room_capacity = room.get("adults", 0)
                    result_lines.append(f"  - {room_name}: {room_price}, 可住{room_capacity}人\n")

            # 旅館簡介
            intro = hotel.get("intro", "")
            if intro:
                # 取簡介的前150個字符並加上省略號
                short_intro = intro[:150] + "..." if len(intro) > 150 else intro
                result_lines.append(f"簡介: {short_intro}\n")

            # 添加分隔符
            result_lines.append("\n")

        return "".join(result_lines)

    def _format_plans_for_llm(self, plans: list[dict[str, Any]]) -> str:
        """將方案資料格式化為LLM易於理解的文本"""
        if not plans:
            return ""

        result_lines = []
        result_lines.append("特價方案\n\n")

        # 限制處理的方案數量
        max_plans = min(5, len(plans))

        for i, plan in enumerate(plans[:max_plans]):
            name = plan.get("plan_name", "未知方案")
            hotel_name = plan.get("hotel_name", "")
            price = plan.get("price", "")
            discount = plan.get("discount_percent", "")

            # 方案基本資訊 - 使用更簡潔的格式
            result_lines.append(f"方案{i + 1}: {name}\n")
            result_lines.append(f"旅館: {hotel_name}\n")
            result_lines.append(f"價格: {price}")

            if discount:
                result_lines.append(f" (折扣: {discount})")

            result_lines.append("\n")

            # 日期範圍
            date_range = self._format_date_range(plan.get("start_date"), plan.get("end_date"))
            if date_range and date_range != "不限日期":
                result_lines.append(f"有效期間: {date_range}\n")

            # 方案描述
            description = plan.get("description", "")
            if description:
                # 取描述的前150個字符並加上省略號
                short_desc = description[:150] + "..." if len(description) > 150 else description
                result_lines.append(f"內容: {short_desc}\n")

            # 方案條款 - 使用簡潔的清單格式
            terms = plan.get("terms", [])
            if terms and isinstance(terms, list) and terms:
                result_lines.append("條款:\n")
                for term in terms[:3]:  # 限制顯示的條款數量
                    result_lines.append(f"  - {term}\n")

            # 適用房型 - 使用簡潔的清單格式
            room_types = plan.get("room_types", [])
            if room_types and isinstance(room_types, list) and room_types:
                result_lines.append("適用房型:\n")
                for room in room_types[:2]:  # 限制顯示的房型數量
                    result_lines.append(f"  - {room.get('name', '')}\n")

            # 添加分隔符
            result_lines.append("\n")

        return "".join(result_lines)


# 創建回應生成Agent實例
response_generator_agent = ResponseGeneratorAgent()
