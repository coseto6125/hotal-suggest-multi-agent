"""
旅館類型解析子Agent，專門負責解析查詢中的旅館類型
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent


class HotelTypeParserAgent(BaseAgent):
    """旅館類型解析子Agent"""

    def __init__(self):
        """初始化旅館類型解析子Agent"""
        super().__init__("HotelTypeParserAgent")
        # 旅館類型關鍵詞映射
        self.hotel_type_keywords = {
            "BASIC": ["基本", "標準", "一般", "普通"],
            "HOTEL": ["飯店", "酒店", "旅館", "旅店"],
            "RESORT": ["度假村", "度假酒店", "度假飯店", "渡假村"],
            "HOSTEL": ["青年旅館", "青旅", "背包客棧", "背包客", "背包房"],
            "HOMESTAY": ["民宿", "家庭旅館", "家庭式", "家庭住宿"],
            "VILLA": ["別墅", "villa", "獨棟", "獨立屋"],
            "APARTMENT": ["公寓", "套房", "apartment", "服務式公寓"],
            "CAMPING": ["露營", "營地", "帳篷", "露營地", "露營區"],
            "GLAMPING": ["豪華露營", "精緻露營", "奢華露營", "glamping"],
            "BNB": ["B&B", "bed and breakfast", "早餐旅館"],
            "LUXURY": ["豪華", "奢華", "高級", "五星", "五星級"],
            "BUDGET": ["經濟", "便宜", "平價", "實惠", "預算"],
            "BOUTIQUE": ["精品", "特色", "設計", "藝術", "boutique"],
            "HOT_SPRING": ["溫泉", "湯屋", "泡湯", "溫泉旅館", "溫泉飯店"],
            "SEASIDE": ["海邊", "海濱", "濱海", "海景", "海岸"],
            "MOUNTAIN": ["山區", "山上", "山景", "高山", "森林"],
            "CITY": ["市區", "市中心", "都市", "市內", "市區"],
        }
        # 旅館類型正則表達式模式
        self.hotel_type_patterns = {}
        for hotel_type, keywords in self.hotel_type_keywords.items():
            pattern = "|".join(keywords)
            self.hotel_type_patterns[hotel_type] = re.compile(f"({pattern})")

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理旅館類型解析請求"""
        logger.debug(f"[{self.name}] 開始處理旅館類型解析請求")

        # 從輸入中提取查詢和上下文
        query = state.get("query", "")
        context = state.get("context", {})

        try:
            if not query:
                # 如果沒有查詢文本，嘗試從上下文或其他字段獲取信息
                if "hotel_type" in context:
                    return {"hotel_type": context["hotel_type"]}

                logger.warning("查詢內容為空，無法解析旅館類型")
                return {"hotel_type": "BASIC", "message": "無法從查詢中提取旅館類型，使用預設類型：BASIC"}

            # 首先嘗試使用正則表達式解析
            hotel_type = self._extract_hotel_type_with_regex(query)

            # 如果正則表達式無法解析，嘗試使用LLM
            # if not hotel_type:
            #     logger.debug("正則表達式無法解析旅館類型，嘗試使用LLM")
            #     hotel_type = await self._extract_hotel_type_with_llm(query)

            # 如果仍然無法解析，使用預設值
            if not hotel_type:
                logger.info("無法從查詢中提取旅館類型，使用預設類型：BASIC")
                return {"hotel_type": "BASIC", "message": "無法從查詢中提取旅館類型，使用預設類型：BASIC"}

            return {"hotel_type": hotel_type}

        except Exception as e:
            logger.error(f"[{self.name}] 旅館類型解析失敗: {e}")
            return {"hotel_type": "BASIC", "message": f"旅館類型解析失敗，使用預設類型：BASIC（錯誤：{e!s}）"}

    def _extract_hotel_type_with_regex(self, query: str) -> str:
        """使用正則表達式從查詢中提取旅館類型"""
        # 記錄匹配到的類型及其出現次數
        type_counts = {}

        for hotel_type, pattern in self.hotel_type_patterns.items():
            matches = pattern.findall(query)
            if matches:
                type_counts[hotel_type] = len(matches)
                logger.debug(f"從查詢中提取到旅館類型: {hotel_type}，匹配次數: {len(matches)}")

        # 如果有匹配到類型，返回出現次數最多的類型
        if type_counts:
            max_type = max(type_counts.items(), key=lambda x: x[1])[0]
            logger.info(f"從查詢中提取到最可能的旅館類型: {max_type}")
            return max_type

        return ""

    async def _extract_hotel_type_with_llm(self, query: str) -> str:
        """使用LLM從查詢中提取旅館類型"""
        # 構建類型列表字符串
        type_list = ", ".join(self.hotel_type_keywords.keys())

        system_prompt = f"""
        你是一個旅館預訂系統的旅館類型解析器。
        你的任務是從用戶的自然語言查詢中提取旅館類型。
        請從以下類型中選擇一個最匹配的：
        {type_list}
        
        如果查詢中沒有明確提到旅館類型，請根據上下文推斷。
        如果無法推斷，請返回 "BASIC"。
        
        請直接返回類型代碼，不要添加任何其他內容。
        """

        response_format = {"type": str}

        # 使用共用方法提取旅館類型
        response = await self._extract_with_llm(
            prompt=f"從以下查詢中提取旅館類型：{query}", system_prompt=system_prompt
        )

        # 如果回應是字符串，進行處理
        if isinstance(response, dict) and "type" in response:
            # 清理回應
            hotel_type = response["type"].strip().upper()

            # 檢查回應是否為有效的類型
            if hotel_type in self.hotel_type_keywords:
                logger.info(f"LLM解析到旅館類型: {hotel_type}")
                return hotel_type

            # 如果不是有效類型，嘗試從回應中提取有效類型
            for hotel_type in self.hotel_type_keywords:
                if hotel_type in response["type"]:
                    logger.info(f"從LLM回應中提取到旅館類型: {hotel_type}")
                    return hotel_type

            logger.warning(f"LLM回應不包含有效的旅館類型: {response['type']}")
        else:
            logger.warning(f"LLM回應格式不正確: {response}")

        return ""