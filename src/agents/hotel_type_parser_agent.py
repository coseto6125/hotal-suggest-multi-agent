"""
旅館類型解析子Agent，專門負責解析查詢中的旅館類型
"""

import re
from typing import Any

from loguru import logger

from src.agents.base_sub_agent import BaseSubAgent
from src.services.llm_service import llm_service


class HotelTypeParserAgent(BaseSubAgent):
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

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的旅館類型"""
        logger.info(f"解析查詢中的旅館類型: {query}")

        # 嘗試使用正則表達式解析旅館類型
        hotel_type = self._extract_hotel_type_with_regex(query)

        # 如果正則表達式無法解析，使用LLM解析
        if not hotel_type:
            hotel_type = await self._extract_hotel_type_with_llm(query)

        # 如果仍然無法解析，設置為默認值
        if not hotel_type:
            hotel_type = "BASIC"  # 默認為基本類型
            logger.info("無法解析旅館類型，使用默認值: BASIC")

        return {"hotel_type": hotel_type}

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

        messages = [{"role": "user", "content": f"從以下查詢中提取旅館類型：{query}"}]
        response = await llm_service.generate_response(messages, system_prompt)

        # 清理回應
        response = response.strip().upper()

        # 檢查回應是否為有效的類型
        if response in self.hotel_type_keywords:
            logger.info(f"LLM解析到旅館類型: {response}")
            return response

        # 如果不是有效類型，嘗試從回應中提取有效類型
        for hotel_type in self.hotel_type_keywords:
            if hotel_type in response:
                logger.info(f"從LLM回應中提取到旅館類型: {hotel_type}")
                return hotel_type

        logger.warning(f"LLM回應不包含有效的旅館類型: {response}")
        return ""


# 創建旅館類型解析子Agent實例
hotel_type_parser_agent = HotelTypeParserAgent()
