"""
Orchestrator Agent 模組

負責協調和管理所有子 Agent 的工作流程。
"""

import asyncio
from typing import Any

from loguru import logger

from src.agents.base.base_agent import BaseAgent

# 移除 ResponseGeneratorAgent 的直接導入，避免循環導入問題
# from src.agents.generators.response_generator_agent import ResponseGeneratorAgent
from src.agents.parsers.budget_parser_agent import BudgetParserAgent
from src.agents.parsers.date_parser_agent import DateParserAgent
from src.agents.parsers.food_req_parser_agent import FoodReqParserAgent
from src.agents.parsers.geo_parser_agent import GeoParserAgent
from src.agents.parsers.guest_parser_agent import GuestParserAgent
from src.agents.parsers.hotel_type_parser_agent import HotelTypeParserAgent
from src.agents.parsers.keyword_parser_agent import KeywordParserAgent
from src.agents.parsers.special_req_parser_agent import SpecialReqParserAgent
from src.agents.parsers.supply_parser_agent import SupplyParserAgent
from src.agents.search.hotel_search_agent import HotelSearchAgent
from src.agents.search.hotel_search_fuzzy_agent import HotelSearchFuzzyAgent
from src.agents.search.hotel_search_plan_agent import HotelSearchPlanAgent


class OrchestratorAgent(BaseAgent):
    """Orchestrator Agent 類別"""

    def __init__(self):
        """初始化 OrchestratorAgent"""
        super().__init__("Orchestrator")
        # 初始化解析 Agent
        self.parser_agents = {
            "budget": BudgetParserAgent(),
            "date": DateParserAgent(),
            "food": FoodReqParserAgent(),
            "geo": GeoParserAgent(),
            "guest": GuestParserAgent(),
            "hotel_type": HotelTypeParserAgent(),
            "keyword": KeywordParserAgent(),
            "special_req": SpecialReqParserAgent(),
            "supply": SupplyParserAgent(),
        }
        # 初始化搜索 Agent
        self.search_agents = {
            "basic": HotelSearchAgent(),
            "fuzzy": HotelSearchFuzzyAgent(),
            "plan": HotelSearchPlanAgent(),
        }
        # 初始化回應生成 Agent
        # self.response_generator = ResponseGeneratorAgent()

    async def _process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理工作流程狀態"""
        try:
            # 執行解析階段
            parsed_data = await self._run_parsing_agents(state)
            state["parsed_data"] = parsed_data

            # 執行搜索階段
            search_results = await self._run_search_agents(state)
            state["search_results"] = search_results

            # 生成回應
            response = await self._generate_response(state)
            state["response"] = response

            return state
        except Exception as e:
            logger.error(f"Orchestrator 處理失敗: {e}")
            return {"error": str(e)}

    async def _run_parsing_agents(self, state: dict[str, Any]) -> dict[str, Any]:
        """執行所有解析 Agent"""
        try:
            user_query = state.get("user_query", "")
            if not user_query:
                logger.warning("用戶查詢為空，無法進行解析")
                return {}

            # 創建所有解析任務
            parser_tasks = []
            for name, agent in self.parser_agents.items():
                # 使用簡單的參數傳遞，只傳遞用戶查詢，避免狀態並發問題
                task = asyncio.create_task(self._run_single_parser(agent, user_query))
                parser_tasks.append((name, task))

            # 等待所有任務完成
            results = {}
            for name, task in parser_tasks:
                try:
                    result = await task
                    if result:
                        results[name] = result
                except Exception as e:
                    logger.error(f"解析 Agent {name} 執行失敗: {e}")
                    results[name] = self._get_default_value(name)

            # 返回新的 parsed_data 字典，而不是修改原始狀態
            return results
        except Exception as e:
            logger.error(f"解析階段執行失敗: {e}")
            return {}

    async def _run_single_parser(self, agent: BaseAgent, user_query: str) -> dict[str, Any] | None:
        """執行單個解析 Agent"""
        try:
            # 只傳遞用戶查詢，避免狀態並發問題
            return await agent.process_query(user_query)
        except Exception as e:
            logger.error(f"解析 Agent {agent.name} 執行失敗: {e}")
            return None

    async def _run_search_agents(self, state: dict[str, Any]) -> dict[str, Any]:
        """執行所有搜索 Agent"""
        try:
            parsed_data = state.get("parsed_data", {})

            # 檢查是否有基本搜索參數
            if not self._has_basic_search_params(parsed_data):
                logger.warning("缺少基本搜索參數，無法進行搜索")
                return {}

            # 準備基本搜索參數
            basic_search_params = self._prepare_basic_search_params(parsed_data)

            # 執行基本搜索
            basic_results = await self.search_agents["basic"].process(basic_search_params)
            if not basic_results:
                logger.warning("基本搜索沒有結果")
                return {}

            # 準備模糊搜索和方案搜索參數
            search_tasks = []

            # 檢查是否有關鍵字資料
            if "keyword" in parsed_data:
                # 模糊搜索參數
                fuzzy_params = {"hotel_name": parsed_data["keyword"].get("hotel_keyword", "")}
                if fuzzy_params["hotel_name"]:
                    fuzzy_task = asyncio.create_task(self.search_agents["fuzzy"].process(fuzzy_params))
                    search_tasks.append(("fuzzy", fuzzy_task))

                # 方案搜索參數 - 需要同時有關鍵字和日期
                if "date" in parsed_data:
                    plan_params = {
                        "hotel_keyword": parsed_data["keyword"].get("hotel_keyword", ""),
                        "plan_keyword": parsed_data["keyword"].get("plan_keyword", ""),
                        "check_in_start_at": parsed_data["date"].get("check_in", ""),
                        "check_in_end_at": parsed_data["date"].get("check_out", ""),
                    }
                    if plan_params["hotel_keyword"] and plan_params["check_in_start_at"]:
                        plan_task = asyncio.create_task(self.search_agents["plan"].process(plan_params))
                        search_tasks.append(("plan", plan_task))

            # 等待所有任務完成
            results = {"basic": basic_results}
            for name, task in search_tasks:
                try:
                    result = await task
                    if result:
                        results[name] = result
                except Exception as e:
                    logger.error(f"搜索 Agent {name} 執行失敗: {e}")

            return results
        except Exception as e:
            logger.error(f"搜索階段執行失敗: {e}")
            return {}

    def _prepare_basic_search_params(self, parsed_data: dict[str, Any]) -> dict[str, Any]:
        """準備基本搜索參數"""
        params = {}

        # 添加旅館類型參數
        if "hotel_type" in parsed_data:
            params["hotel_group_types"] = str(parsed_data["hotel_type"].get("hotel_group_types", ""))

        # 添加日期參數
        if "date" in parsed_data:
            params["check_in"] = str(parsed_data["date"].get("check_in", ""))
            params["check_out"] = str(parsed_data["date"].get("check_out", ""))

        # 添加住客參數
        if "guest" in parsed_data:
            params["adults"] = int(parsed_data["guest"].get("adults", 1))
            params["children"] = int(parsed_data["guest"].get("children", 0))

        # 添加預算參數
        if "budget" in parsed_data:
            params["lowest_price"] = int(parsed_data["budget"].get("lowest_price", 0))
            params["highest_price"] = int(parsed_data["budget"].get("highest_price", 0))

        # 添加地理位置參數
        if "geo" in parsed_data:
            params["county_ids[]"] = list(parsed_data["geo"].get("county_ids", []))
            params["district_ids[]"] = list(parsed_data["geo"].get("district_ids", []))

        # 添加設施參數
        if "special_req" in parsed_data:
            params["hotel_facility_ids[]"] = list(parsed_data["special_req"].get("hotel_facility_ids", []))
            params["room_facility_ids[]"] = list(parsed_data["special_req"].get("room_facility_ids", []))

        # 添加餐食參數
        if "food" in parsed_data:
            params["has_breakfast"] = bool(parsed_data["food"].get("has_breakfast", False))
            params["has_lunch"] = bool(parsed_data["food"].get("has_lunch", False))
            params["has_dinner"] = bool(parsed_data["food"].get("has_dinner", False))

        return params

    async def _generate_response(self, state: dict[str, Any]) -> dict[str, Any]:
        """生成回應"""
        try:
            # 檢查是否有搜索結果
            if not state.get("search_results"):
                return {"message": "抱歉，沒有找到符合條件的旅館。請嘗試調整搜索條件。", "status": "no_results"}

            # 簡單生成回應
            search_results = state["search_results"]
            basic_results = search_results.get("basic", [])
            fuzzy_results = search_results.get("fuzzy", [])
            plan_results = search_results.get("plan", [])

            # 合併所有結果
            all_hotels = basic_results + fuzzy_results

            # 生成回應文本
            response_text = f"我找到了 {len(all_hotels)} 個符合您要求的旅館。"
            if plan_results:
                response_text += f" 其中 {len(plan_results)} 個有特別方案。"

            # 將前3個旅館添加到回應
            if all_hotels:
                response_text += "\n\n推薦旅館：\n"
                for i, hotel in enumerate(all_hotels[:3], 1):
                    name = hotel.get("name", "未知旅館")
                    address = hotel.get("address", "地址未提供")
                    price = hotel.get("price", "價格未提供")
                    response_text += f"{i}. {name} - {address}, 價格約 NT${price}\n"

            return {"message": response_text, "status": "success", "hotels": all_hotels[:5], "plans": plan_results[:3]}
        except Exception as e:
            logger.error(f"回應生成失敗: {e}")
            return {"message": "抱歉，生成回應時發生錯誤。", "status": "error"}

    def _get_default_value(self, parser_name: str) -> dict[str, Any]:
        """獲取解析失敗時的預設值"""
        defaults = {
            "budget": {"min": 0, "max": float("inf")},
            "date": {"check_in": None, "check_out": None},
            "food": {"breakfast": False, "lunch": False, "dinner": False},
            "geo": {"city": None, "district": None, "address": None},
            "guest": {"adults": 1, "children": 0},
            "hotel_type": {"type": "hotel"},
            "keyword": {"keywords": []},
            "special_req": {"requirements": []},
            "supply": {"supplier": None},
        }
        return defaults.get(parser_name, {})

    def _has_basic_search_params(self, parsed_data: dict[str, Any]) -> bool:
        """檢查是否有基本搜索參數"""
        required_params = ["geo", "date", "guest"]
        return all(param in parsed_data for param in required_params)


# 創建 OrchestratorAgent 實例
orchestrator = OrchestratorAgent()
