"""
特殊需求解析子Agent，專門負責解析查詢中的特殊需求
"""

import re
from typing import Any

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent
from src.services.llm_service import llm_service


class SpecialReqParserAgent(BaseSubAgent):
    """特殊需求解析子Agent"""

    def __init__(self):
        """初始化特殊需求解析子Agent"""
        super().__init__("SpecialReqParserAgent")
        # 特殊需求關鍵詞映射
        self.facility_keywords = {
            # 旅館設施
            "WIFI": ["wifi", "無線網路", "網路", "上網", "網絡"],
            "PARKING": ["停車場", "停車", "車位", "泊車"],
            "POOL": ["游泳池", "泳池", "水池"],
            "GYM": ["健身房", "健身中心", "健身設施", "健身"],
            "SPA": ["水療", "按摩", "spa", "水療中心"],
            "RESTAURANT": ["餐廳", "餐館", "餐飲", "用餐"],
            "BAR": ["酒吧", "吧台", "bar"],
            "LOUNGE": ["休息室", "休息區", "lounge"],
            "BUSINESS_CENTER": ["商務中心", "會議室", "商務設施"],
            "KIDS_CLUB": ["兒童樂園", "兒童俱樂部", "兒童設施", "兒童遊戲區"],
            "BEACH": ["沙灘", "海灘", "私人沙灘", "私人海灘"],
            "GARDEN": ["花園", "庭院", "園景"],
            "TERRACE": ["露台", "陽台", "平台"],
            "ELEVATOR": ["電梯", "升降機"],
            "AIRPORT_SHUTTLE": ["機場接送", "接機", "送機", "機場巴士"],
            "CONCIERGE": ["禮賓服務", "管家服務", "禮賓"],
            "LAUNDRY": ["洗衣服務", "洗衣", "洗衣設施"],
            "ROOM_SERVICE": ["客房服務", "送餐服務"],
            "WHEELCHAIR_ACCESSIBLE": ["無障礙設施", "輪椅通道", "無障礙"],
            "PET_FRIENDLY": ["寵物友好", "可帶寵物", "寵物", "攜帶寵物"],
            # 房間設施
            "AIR_CONDITIONING": ["空調", "冷氣", "冷暖氣"],
            "HEATING": ["暖氣", "暖爐", "電暖器"],
            "TV": ["電視", "液晶電視", "平面電視", "電視機"],
            "REFRIGERATOR": ["冰箱", "小冰箱", "迷你冰箱"],
            "MICROWAVE": ["微波爐", "微波"],
            "COFFEE_MAKER": ["咖啡機", "咖啡壺", "咖啡設備"],
            "KETTLE": ["電熱水壺", "熱水壺", "煮水壺"],
            "HAIR_DRYER": ["吹風機", "電吹風", "風筒"],
            "IRON": ["熨斗", "熨衣設備", "熨衣板"],
            "SAFE": ["保險箱", "保險櫃", "保險柜"],
            "DESK": ["書桌", "工作桌", "辦公桌"],
            "BALCONY": ["陽台", "露台", "戶外空間"],
            "BATHTUB": ["浴缸", "浴池", "泡澡"],
            "SHOWER": ["淋浴", "蓮蓬頭", "沖涼"],
            "TOILETRIES": ["盥洗用品", "洗漱用品", "沐浴用品"],
            "SLIPPERS": ["拖鞋", "室內拖鞋"],
            "BATHROBES": ["浴袍", "浴衣"],
            "SOUNDPROOF": ["隔音", "隔音設施", "靜音"],
            "BLACKOUT_CURTAINS": ["遮光窗簾", "窗簾", "遮光"],
            "WAKE_UP_SERVICE": ["喚醒服務", "鬧鐘服務", "叫醒服務"],
            # 餐飲相關
            "BREAKFAST": ["早餐", "早點", "早飯"],
            "LUNCH": ["午餐", "午飯", "中餐"],
            "DINNER": ["晚餐", "晚飯", "夜餐"],
            "ALL_INCLUSIVE": ["全包式", "全包", "一價全包"],
            "BUFFET": ["自助餐", "buffet", "自助式"],
            "VEGETARIAN": ["素食", "蔬食", "素食選擇"],
            "VEGAN": ["純素", "全素", "vegan"],
            "GLUTEN_FREE": ["無麩質", "gluten free"],
            "HALAL": ["清真", "哈拉", "halal"],
            "KOSHER": ["猶太", "kosher"],
            # 景觀相關
            "SEA_VIEW": ["海景", "海景房", "看海"],
            "MOUNTAIN_VIEW": ["山景", "山景房", "看山"],
            "CITY_VIEW": ["城市景觀", "市景", "都市景觀"],
            "GARDEN_VIEW": ["花園景觀", "園景", "庭院景觀"],
            "LAKE_VIEW": ["湖景", "湖景房", "看湖"],
            "RIVER_VIEW": ["河景", "河景房", "看河"],
            # 床型相關
            "KING_BED": ["特大床", "king size", "king bed"],
            "QUEEN_BED": ["大床", "queen size", "queen bed"],
            "TWIN_BEDS": ["雙床", "兩張單人床", "twin beds"],
            "SINGLE_BED": ["單人床", "單床", "single bed"],
            "SOFA_BED": ["沙發床", "梳化床", "sofa bed"],
            "EXTRA_BED": ["加床", "額外床", "extra bed"],
            # 其他特殊需求
            "QUIET_ROOM": ["安靜房間", "安靜", "寧靜"],
            "HIGH_FLOOR": ["高樓層", "高層", "高樓"],
            "LOW_FLOOR": ["低樓層", "低層", "低樓"],
            "CONNECTING_ROOMS": ["相連房", "連通房", "connecting rooms"],
            "HONEYMOON": ["蜜月", "新婚", "honeymoon"],
            "ANNIVERSARY": ["週年紀念", "紀念日", "anniversary"],
            "BIRTHDAY": ["生日", "慶生", "birthday"],
            "LATE_CHECK_OUT": ["延遲退房", "晚退房", "late check out"],
            "EARLY_CHECK_IN": ["提前入住", "早入住", "early check in"],
        }

        # 特殊需求正則表達式模式
        self.facility_patterns = {}
        for facility_type, keywords in self.facility_keywords.items():
            pattern = "|".join(keywords)
            self.facility_patterns[facility_type] = re.compile(f"({pattern})")

        # 餐食相關正則表達式
        self.breakfast_pattern = re.compile(r"(?:含|有|帶|提供|供應|免費)(?:早餐|早點|早飯)")
        self.lunch_pattern = re.compile(r"(?:含|有|帶|提供|供應|免費)(?:午餐|午飯|中餐)")
        self.dinner_pattern = re.compile(r"(?:含|有|帶|提供|供應|免費)(?:晚餐|晚飯|夜餐)")

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的特殊需求"""
        logger.info(f"解析查詢中的特殊需求: {query}")

        # 使用正則表達式解析特殊需求
        special_reqs = self._extract_special_reqs_with_regex(query)

        # 使用LLM增強解析結果
        llm_reqs = await self._extract_special_reqs_with_llm(query, special_reqs)

        # 合併結果
        special_reqs.update(llm_reqs)

        # 構建結果
        result = {
            "hotel_facility_ids": special_reqs.get("hotel_facilities", []),
            "room_facility_ids": special_reqs.get("room_facilities", []),
            "has_breakfast": special_reqs.get("has_breakfast", False),
            "has_lunch": special_reqs.get("has_lunch", False),
            "has_dinner": special_reqs.get("has_dinner", False),
            "special_requirements": special_reqs.get("special_requirements", []),
        }

        return result

    def _extract_special_reqs_with_regex(self, query: str) -> dict[str, Any]:
        """使用正則表達式從查詢中提取特殊需求"""
        # 初始化結果
        special_reqs = {
            "hotel_facilities": [],
            "room_facilities": [],
            "has_breakfast": False,
            "has_lunch": False,
            "has_dinner": False,
            "special_requirements": [],
        }

        # 旅館設施和房間設施的ID映射
        hotel_facilities = [
            "WIFI",
            "PARKING",
            "POOL",
            "GYM",
            "SPA",
            "RESTAURANT",
            "BAR",
            "LOUNGE",
            "BUSINESS_CENTER",
            "KIDS_CLUB",
            "BEACH",
            "GARDEN",
            "TERRACE",
            "ELEVATOR",
            "AIRPORT_SHUTTLE",
            "CONCIERGE",
            "LAUNDRY",
            "ROOM_SERVICE",
            "WHEELCHAIR_ACCESSIBLE",
            "PET_FRIENDLY",
        ]

        room_facilities = [
            "AIR_CONDITIONING",
            "HEATING",
            "TV",
            "REFRIGERATOR",
            "MICROWAVE",
            "COFFEE_MAKER",
            "KETTLE",
            "HAIR_DRYER",
            "IRON",
            "SAFE",
            "DESK",
            "BALCONY",
            "BATHTUB",
            "SHOWER",
            "TOILETRIES",
            "SLIPPERS",
            "BATHROBES",
            "SOUNDPROOF",
            "BLACKOUT_CURTAINS",
            "WAKE_UP_SERVICE",
        ]

        # 提取旅館設施和房間設施
        for facility_type, pattern in self.facility_patterns.items():
            if pattern.search(query):
                if facility_type in hotel_facilities:
                    special_reqs["hotel_facilities"].append(facility_type)
                    logger.debug(f"從查詢中提取到旅館設施: {facility_type}")
                elif facility_type in room_facilities:
                    special_reqs["room_facilities"].append(facility_type)
                    logger.debug(f"從查詢中提取到房間設施: {facility_type}")
                else:
                    special_reqs["special_requirements"].append(facility_type)
                    logger.debug(f"從查詢中提取到特殊需求: {facility_type}")

        # 提取餐食相關需求
        if self.breakfast_pattern.search(query) or "BREAKFAST" in special_reqs["special_requirements"]:
            special_reqs["has_breakfast"] = True
            logger.debug("從查詢中提取到早餐需求")

            # 從特殊需求中移除早餐，避免重複
            if "BREAKFAST" in special_reqs["special_requirements"]:
                special_reqs["special_requirements"].remove("BREAKFAST")

        if self.lunch_pattern.search(query) or "LUNCH" in special_reqs["special_requirements"]:
            special_reqs["has_lunch"] = True
            logger.debug("從查詢中提取到午餐需求")

            # 從特殊需求中移除午餐，避免重複
            if "LUNCH" in special_reqs["special_requirements"]:
                special_reqs["special_requirements"].remove("LUNCH")

        if self.dinner_pattern.search(query) or "DINNER" in special_reqs["special_requirements"]:
            special_reqs["has_dinner"] = True
            logger.debug("從查詢中提取到晚餐需求")

            # 從特殊需求中移除晚餐，避免重複
            if "DINNER" in special_reqs["special_requirements"]:
                special_reqs["special_requirements"].remove("DINNER")

        return special_reqs

    async def _extract_special_reqs_with_llm(self, query: str, regex_reqs: dict[str, Any]) -> dict[str, Any]:
        """使用LLM從查詢中提取特殊需求"""
        # 構建設施列表字符串
        hotel_facilities_str = ", ".join(
            [
                f
                for f in self.facility_keywords
                if f
                in [
                    "WIFI",
                    "PARKING",
                    "POOL",
                    "GYM",
                    "SPA",
                    "RESTAURANT",
                    "BAR",
                    "LOUNGE",
                    "BUSINESS_CENTER",
                    "KIDS_CLUB",
                    "BEACH",
                    "GARDEN",
                    "TERRACE",
                    "ELEVATOR",
                    "AIRPORT_SHUTTLE",
                    "CONCIERGE",
                    "LAUNDRY",
                    "ROOM_SERVICE",
                    "WHEELCHAIR_ACCESSIBLE",
                    "PET_FRIENDLY",
                ]
            ]
        )

        room_facilities_str = ", ".join(
            [
                f
                for f in self.facility_keywords
                if f
                in [
                    "AIR_CONDITIONING",
                    "HEATING",
                    "TV",
                    "REFRIGERATOR",
                    "MICROWAVE",
                    "COFFEE_MAKER",
                    "KETTLE",
                    "HAIR_DRYER",
                    "IRON",
                    "SAFE",
                    "DESK",
                    "BALCONY",
                    "BATHTUB",
                    "SHOWER",
                    "TOILETRIES",
                    "SLIPPERS",
                    "BATHROBES",
                    "SOUNDPROOF",
                    "BLACKOUT_CURTAINS",
                    "WAKE_UP_SERVICE",
                ]
            ]
        )

        # 已經通過正則表達式識別的設施
        identified_hotel_facilities = ", ".join(regex_reqs["hotel_facilities"])
        identified_room_facilities = ", ".join(regex_reqs["room_facilities"])
        identified_special_reqs = ", ".join(regex_reqs["special_requirements"])

        system_prompt = f"""
        你是一個旅館預訂系統的特殊需求解析器。
        你的任務是從用戶的自然語言查詢中提取特殊需求。
        
        我們已經通過正則表達式識別出以下需求：
        旅館設施: {identified_hotel_facilities}
        房間設施: {identified_room_facilities}
        特殊需求: {identified_special_reqs}
        早餐: {"是" if regex_reqs["has_breakfast"] else "否"}
        午餐: {"是" if regex_reqs["has_lunch"] else "否"}
        晚餐: {"是" if regex_reqs["has_dinner"] else "否"}
        
        請檢查是否有我們遺漏的需求，並從以下類別中選擇：
        
        旅館設施: {hotel_facilities_str}
        
        房間設施: {room_facilities_str}
        
        請以JSON格式返回結果，格式如下：
        {{
            "hotel_facilities": ["FACILITY_ID1", "FACILITY_ID2", ...],
            "room_facilities": ["FACILITY_ID1", "FACILITY_ID2", ...],
            "has_breakfast": true/false,
            "has_lunch": true/false,
            "has_dinner": true/false,
            "special_requirements": ["REQUIREMENT1", "REQUIREMENT2", ...]
        }}
        
        只返回我們遺漏的需求，已識別的需求不需要重複返回。
        如果沒有遺漏的需求，請返回空列表。
        """

        messages = [{"role": "user", "content": f"從以下查詢中提取特殊需求：{query}"}]
        response = await llm_service.generate_response(messages, system_prompt)

        try:
            # 使用正則表達式提取JSON
            json_pattern = re.compile(r"{.*}", re.DOTALL)
            match = json_pattern.search(response)
            if match:
                import orjson

                llm_reqs = orjson.loads(match.group(0))

                # 記錄LLM識別的額外需求
                if llm_reqs.get("hotel_facilities"):
                    logger.info(f"LLM識別的額外旅館設施: {llm_reqs['hotel_facilities']}")
                if llm_reqs.get("room_facilities"):
                    logger.info(f"LLM識別的額外房間設施: {llm_reqs['room_facilities']}")
                if llm_reqs.get("special_requirements"):
                    logger.info(f"LLM識別的額外特殊需求: {llm_reqs['special_requirements']}")

                return llm_reqs
        except Exception as e:
            logger.error(f"LLM特殊需求解析失敗: {e!s}")

        return {}


# 創建特殊需求解析子Agent實例
special_req_parser_agent = SpecialReqParserAgent()
