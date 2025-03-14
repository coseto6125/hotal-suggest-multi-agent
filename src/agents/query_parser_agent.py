"""
查詢解析Agent，負責解析用戶查詢
"""

from typing import Any

from loguru import logger
from opencc import OpenCC

from src.agents.base_agent import BaseAgent
from src.agents.budget_parser_agent import budget_parser_agent
from src.agents.date_parser_agent import date_parser_agent
from src.agents.geo_parser_agent import geo_parser_agent
from src.agents.guest_parser_agent import guest_parser_agent
from src.agents.hotel_type_parser_agent import hotel_type_parser_agent
from src.agents.keyword_parser_agent import keyword_parser_agent
from src.agents.special_req_parser_agent import special_req_parser_agent
from src.agents.supply_parser_agent import supply_parser_agent
from src.cache.geo_cache import geo_cache


class QueryParserAgent(BaseAgent):
    """查詢解析Agent"""

    def __init__(self):
        """初始化查詢解析Agent"""
        super().__init__("QueryParserAgent")
        self.cc = OpenCC("s2twp")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理用戶查詢"""
        user_query = inputs.get("user_query", "")
        user_query = self.cc.convert(user_query)

        if not user_query:
            return {"error": "用戶查詢為空"}

        logger.info(f"解析用戶查詢: {user_query}")

        # 確保地理資料快取已初始化
        if not geo_cache._initialized:
            logger.info("地理資料快取尚未初始化，正在初始化...")
            await geo_cache.initialize()

        # 創建上下文字典，用於在各個子Agent之間共享資訊
        context = {}

        # 0. 使用備品搜尋子Agent解析房間備品名稱
        supply_result = await supply_parser_agent.process_query(user_query, context)
        context.update(supply_result)
        logger.info(f"備品搜尋解析結果: {supply_result}")

        # 如果是備品搜尋模式，直接返回結果
        if context.get("is_supply_search", False):
            parsed_query = {
                "original_query": user_query,
                "search_mode": "supply",
                "supply_name": context.get("supply_name", ""),
            }
            return {"parsed_query": parsed_query, "original_query": user_query}

        # 1. 使用地理名稱解析子Agent解析地理名稱
        geo_result = await geo_parser_agent.process_query(user_query, context)
        context.update(geo_result)
        logger.info(f"地理名稱解析結果: {geo_result}")

        # 2. 使用日期解析子Agent解析旅遊日期
        date_result = await date_parser_agent.process_query(user_query, context)
        context.update(date_result)
        logger.info(f"日期解析結果: {date_result}")

        # 3. 使用人數解析子Agent解析人數信息
        guest_result = await guest_parser_agent.process_query(user_query, context)
        context.update(guest_result)
        logger.info(f"人數解析結果: {guest_result}")

        # 4. 使用預算解析子Agent解析預算範圍
        budget_result = await budget_parser_agent.process_query(user_query, context)
        context.update(budget_result)
        logger.info(f"預算解析結果: {budget_result}")

        # 5. 使用旅館類型解析子Agent解析旅館類型
        hotel_type_result = await hotel_type_parser_agent.process_query(user_query, context)
        context.update(hotel_type_result)
        logger.info(f"旅館類型解析結果: {hotel_type_result}")

        # 6. 使用特殊需求解析子Agent解析特殊需求
        special_req_result = await special_req_parser_agent.process_query(user_query, context)
        context.update(special_req_result)
        logger.info(f"特殊需求解析結果: {special_req_result}")

        # 7. 使用旅館名稱/關鍵字解析子Agent解析旅館名稱和關鍵字
        keyword_result = await keyword_parser_agent.process_query(user_query, context)
        context.update(keyword_result)
        logger.info(f"旅館名稱/關鍵字解析結果: {keyword_result}")

        # 構建最終的解析結果
        parsed_query = self._build_parsed_query(user_query, context)

        return {"parsed_query": parsed_query, "original_query": user_query}

    def _build_parsed_query(self, user_query: str, context: dict[str, Any]) -> dict[str, Any]:
        """構建最終的解析結果"""
        # 檢查是否是關鍵字搜尋模式
        if context.get("is_keyword_search", False):
            parsed_query = {
                "original_query": user_query,
                "search_mode": "keyword",
                "hotel_keyword": context.get("hotel_keyword", ""),
                "plan_keyword": context.get("plan_keyword", ""),
                "check_in_start_at": context.get("dates", {}).get("check_in"),
                "check_in_end_at": context.get("dates", {}).get("check_out"),
            }
        else:
            # 條件搜尋模式
            parsed_query = {
                "original_query": user_query,
                "search_mode": "filter",
                "hotel_group_types": context.get("hotel_type", "BASIC"),
                "check_in": context.get("dates", {}).get("check_in"),
                "check_out": context.get("dates", {}).get("check_out"),
                "adults": context.get("guests", {}).get("adults"),
                "children": context.get("guests", {}).get("children"),
                "lowest_price": context.get("budget", {}).get("min"),
                "highest_price": context.get("budget", {}).get("max"),
                "county_ids": context.get("county_ids", []),
                "district_ids": context.get("district_ids", []),
                "hotel_facility_ids": context.get("hotel_facility_ids", []),
                "room_facility_ids": context.get("room_facility_ids", []),
                "has_breakfast": context.get("has_breakfast", False),
                "has_lunch": context.get("has_lunch", False),
                "has_dinner": context.get("has_dinner", False),
                "special_requirements": context.get("special_requirements", []),
            }

            # 如果有目的地信息，添加到解析結果中
            if (
                context.get("destination", {}).get("county")
                and context["destination"]["county"] not in parsed_query["county_ids"]
            ):
                parsed_query["county_ids"].append(context["destination"]["county"])
            if (
                context.get("destination", {}).get("district")
                and context["destination"]["district"] not in parsed_query["district_ids"]
            ):
                parsed_query["district_ids"].append(context["destination"]["district"])

        return parsed_query


# 創建查詢解析Agent實例
query_parser_agent = QueryParserAgent()
