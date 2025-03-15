"""
旅館名稱/關鍵字解析子Agent，專門負責解析查詢中的旅館名稱和關鍵字
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent
from src.services.llm_service import llm_service


class KeywordParserAgent(BaseSubAgent):
    """旅館名稱/關鍵字解析子Agent"""

    def __init__(self):
        """初始化旅館名稱/關鍵字解析子Agent"""
        super().__init__("KeywordParserAgent")
        # 旅館名稱/關鍵字正則表達式模式
        self.hotel_name_patterns = [
            re.compile(
                r"(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)「([^」]+)」"
            ),
            re.compile(
                r"(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)『([^』]+)』"
            ),
            re.compile(
                r"(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)\"([^\"]+)\""
            ),
            re.compile(
                r"(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)'([^']+)'"
            ),
            re.compile(
                r"(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)([^\s,，。；;]+)"
            ),
            re.compile(
                r"「([^」]+)」(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)"
            ),
            re.compile(
                r"『([^』]+)』(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)"
            ),
            re.compile(
                r"\"([^\"]+)\"(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)"
            ),
            re.compile(
                r"'([^']+)'(?:飯店|酒店|旅館|旅店|民宿|度假村|青年旅館|青旅|背包客棧|別墅|公寓|套房|營地|露營地|露營區|B&B)"
            ),
        ]

        self.plan_name_patterns = [
            re.compile(
                r"(?:方案|專案|套餐|行程|計劃|計畫|package)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)「([^」]+)」"
            ),
            re.compile(
                r"(?:方案|專案|套餐|行程|計劃|計畫|package)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)『([^』]+)』"
            ),
            re.compile(
                r"(?:方案|專案|套餐|行程|計劃|計畫|package)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)\"([^\"]+)\""
            ),
            re.compile(
                r"(?:方案|專案|套餐|行程|計劃|計畫|package)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)'([^']+)'"
            ),
            re.compile(
                r"(?:方案|專案|套餐|行程|計劃|計畫|package)(?:叫|名為|名字是|名稱是|名叫|叫做|名字叫|名稱叫|叫作|名為)([^\s,，。；;]+)"
            ),
            re.compile(r"「([^」]+)」(?:方案|專案|套餐|行程|計劃|計畫|package)"),
            re.compile(r"『([^』]+)』(?:方案|專案|套餐|行程|計劃|計畫|package)"),
            re.compile(r"\"([^\"]+)\"(?:方案|專案|套餐|行程|計劃|計畫|package)"),
            re.compile(r"'([^']+)'(?:方案|專案|套餐|行程|計劃|計畫|package)"),
        ]

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的旅館名稱和關鍵字"""
        logger.debug(f"[{self.name}] 開始解析關鍵字")
        try:
            if not query:
                raise ValueError("查詢內容為空")

            # 嘗試使用正則表達式解析旅館名稱和關鍵字
            keywords = self._extract_keywords_with_regex(query)

            # 如果正則表達式無法解析，使用LLM解析
            if not keywords["hotel_keyword"] and not keywords["plan_keyword"]:
                llm_keywords = await self._extract_keywords_with_llm(query)

                # 合併結果
                if llm_keywords["hotel_keyword"]:
                    keywords["hotel_keyword"] = llm_keywords["hotel_keyword"]
                if llm_keywords["plan_keyword"]:
                    keywords["plan_keyword"] = llm_keywords["plan_keyword"]

            # 檢查是否是關鍵字搜尋模式
            is_keyword_search = self._is_keyword_search_mode(query, keywords)
            keywords["is_keyword_search"] = is_keyword_search

            return keywords

        except Exception as e:
            logger.debug(f"[{self.name}] 關鍵字解析失敗: {e}")
            return {
                "hotel_keyword": "",
                "plan_keyword": "",
                "is_keyword_search": False,
                "message": f"關鍵字解析失敗（錯誤：{e!s}）",
            }

    def _extract_keywords_with_regex(self, query: str) -> dict[str, Any]:
        """使用正則表達式從查詢中提取旅館名稱和關鍵字"""
        keywords = {"hotel_keyword": "", "plan_keyword": ""}

        # 提取旅館名稱
        for pattern in self.hotel_name_patterns:
            match = pattern.search(query)
            if match:
                keywords["hotel_keyword"] = match.group(1).strip()
                logger.debug(f"從查詢中提取到旅館名稱: {keywords['hotel_keyword']}")
                break

        # 提取方案名稱
        for pattern in self.plan_name_patterns:
            match = pattern.search(query)
            if match:
                keywords["plan_keyword"] = match.group(1).strip()
                logger.debug(f"從查詢中提取到方案名稱: {keywords['plan_keyword']}")
                break

        return keywords

    async def _extract_keywords_with_llm(self, query: str) -> dict[str, Any]:
        """使用LLM從查詢中提取旅館名稱和關鍵字"""
        system_prompt = """
        你是一個旅館預訂系統的關鍵字解析器。
        你的任務是從用戶的自然語言查詢中提取旅館名稱和方案名稱。
        
        請以JSON格式返回結果，格式如下：
        {
            "hotel_keyword": "旅館名稱",
            "plan_keyword": "方案名稱"
        }
        
        如果查詢中沒有明確提到旅館名稱或方案名稱，請返回空字符串。
        """

        messages = [{"role": "user", "content": f"從以下查詢中提取旅館名稱和方案名稱：{query}"}]
        response = await llm_service.generate_response(messages, system_prompt)

        try:
            # 使用正則表達式提取JSON
            json_pattern = re.compile(r"{.*}", re.DOTALL)
            match = json_pattern.search(response)
            if match:
                import orjson

                keywords = orjson.loads(match.group(0))

                # 記錄LLM識別的關鍵字
                if keywords.get("hotel_keyword"):
                    logger.info(f"LLM識別的旅館名稱: {keywords['hotel_keyword']}")
                if keywords.get("plan_keyword"):
                    logger.info(f"LLM識別的方案名稱: {keywords['plan_keyword']}")

                return keywords
        except Exception as e:
            logger.error(f"LLM關鍵字解析失敗: {e!s}")

        return {"hotel_keyword": "", "plan_keyword": ""}

    def _is_keyword_search_mode(self, query: str, keywords: dict[str, str]) -> bool:
        """檢查是否是關鍵字搜尋模式"""
        # 如果有明確的旅館名稱或方案名稱，則是關鍵字搜尋模式
        if keywords["hotel_keyword"] or keywords["plan_keyword"]:
            return True

        # 檢查是否包含特定關鍵詞
        keyword_indicators = [
            "找",
            "搜尋",
            "搜索",
            "查詢",
            "查找",
            "尋找",
            "查",
            "搜",
            "尋",
            "有沒有",
            "有無",
            "有什麼",
            "有哪些",
            "有沒",
            "有無",
            "有什",
            "有哪",
            "推薦",
            "介紹",
            "建議",
            "推",
            "介",
            "薦",
            "議",
        ]

        return any(indicator in query for indicator in keyword_indicators)


# 創建旅館名稱/關鍵字解析子Agent實例
keyword_parser_agent = KeywordParserAgent()
