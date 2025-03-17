"""
解析器實例模組，用於創建和管理所有解析器的實例
"""

import importlib
from typing import Any

from loguru import logger


class LazyParserLoader:
    """延遲加載解析器的類"""

    def __init__(self):
        """初始化延遲加載器"""
        self._instances: dict[str, Any] = {}
        self._initialized = False

    def _initialize(self):
        """初始化所有解析器實例"""
        if self._initialized:
            return

        logger.info("初始化所有解析器實例...")

        # 動態導入所有解析器類
        budget_parser_module = importlib.import_module("src.agents.parsers.budget_parser_agent")
        date_parser_module = importlib.import_module("src.agents.parsers.date_parser_agent")
        food_req_parser_module = importlib.import_module("src.agents.parsers.food_req_parser_agent")
        geo_parser_module = importlib.import_module("src.agents.parsers.geo_parser_agent")
        guest_parser_module = importlib.import_module("src.agents.parsers.guest_parser_agent")
        hotel_type_parser_module = importlib.import_module("src.agents.parsers.hotel_type_parser_agent")
        keyword_parser_module = importlib.import_module("src.agents.parsers.keyword_parser_agent")
        special_req_parser_module = importlib.import_module("src.agents.parsers.special_req_parser_agent")
        supply_parser_module = importlib.import_module("src.agents.parsers.supply_parser_agent")

        # 創建所有解析器的實例
        self._instances["budget_parser_agent"] = budget_parser_module.BudgetParserAgent()
        self._instances["date_parser_agent"] = date_parser_module.DateParserAgent()
        self._instances["food_req_parser_agent"] = food_req_parser_module.FoodReqParserAgent()
        self._instances["geo_parser_agent"] = geo_parser_module.GeoParserAgent()
        self._instances["guest_parser_agent"] = guest_parser_module.GuestParserAgent()
        self._instances["hotel_type_parser_agent"] = hotel_type_parser_module.HotelTypeParserAgent()
        self._instances["keyword_parser_agent"] = keyword_parser_module.KeywordParserAgent()
        self._instances["special_req_parser_agent"] = special_req_parser_module.SpecialReqParserAgent()
        self._instances["supply_parser_agent"] = supply_parser_module.SupplyParserAgent()

        self._initialized = True
        logger.info("所有解析器實例初始化完成")

    def __getattr__(self, name):
        """獲取解析器實例"""
        if not self._initialized:
            self._initialize()

        if name in self._instances:
            return self._instances[name]

        raise AttributeError(f"LazyParserLoader 沒有屬性 '{name}'")


# 創建延遲加載器實例
parsers = LazyParserLoader()

# 導出所有實例
__all__ = ["parsers"]
