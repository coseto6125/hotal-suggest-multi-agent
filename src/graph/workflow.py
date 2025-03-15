from datetime import datetime
from functools import wraps
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger
from opencc import OpenCC
from typing_extensions import Annotated

from src.agents.generators.response_generator_agent import ResponseGeneratorAgent

# 導入所有解析器 agents
from src.agents.parsers.budget_parser_agent import BudgetParserAgent
from src.agents.parsers.date_parser_agent import DateParserAgent
from src.agents.parsers.food_req_parser_agent import FoodReqParserAgent
from src.agents.parsers.geo_parser_agent import GeoParserAgent
from src.agents.parsers.guest_parser_agent import GuestParserAgent
from src.agents.parsers.hotel_type_parser_agent import HotelTypeParserAgent
from src.agents.parsers.keyword_parser_agent import KeywordParserAgent
from src.agents.parsers.special_req_parser_agent import SpecialReqParserAgent
from src.agents.parsers.supply_parser_agent import SupplyParserAgent

# 導入所有搜索 agents
from src.agents.search.hotel_search_agent import HotelSearchAgent
from src.agents.search.hotel_search_fuzzy_agent import HotelSearchFuzzyAgent
from src.agents.search.hotel_search_plan_agent import HotelSearchPlanAgent


# 自定義merge函數用於合併字典
def dict_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """合併兩個字典"""
    result = dict1.copy()
    result.update(dict2)
    return result


# 合併兩個列表，去除重複的酒店
def merge_hotel_results(list1: list[dict[str, Any]], list2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合併酒店搜索結果，去除重複項"""
    result = list1.copy()
    existing_ids = {item.get("hotel_id") for item in result if "hotel_id" in item}

    for item in list2:
        if "hotel_id" in item and item["hotel_id"] not in existing_ids:
            result.append(item)
            existing_ids.add(item["hotel_id"])

    return result


# 合併兩個方案列表，去除重複的方案
def merge_plan_results(list1: list[dict[str, Any]], list2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合併方案搜索結果，去除重複項"""
    result = list1.copy()
    existing_ids = {item.get("plan_id") for item in result if "plan_id" in item}

    for item in list2:
        if "plan_id" in item and item["plan_id"] not in existing_ids:
            result.append(item)
            existing_ids.add(item["plan_id"])

    return result


# 合併兩個整數列表，去除重複項
def merge_unique_ids(list1: list[int], list2: list[int]) -> list[int]:
    """合併兩個ID列表，去除重複項"""
    return list(set(list1 + list2))


# 定義狀態類型，為多節點並行更新的字段添加合併邏輯
class HotelRecommendationState(TypedDict, total=False):
    """旅館推薦工作流狀態定義"""

    query: str
    timestamp: str
    lowest_price: int
    highest_price: int
    check_in: str
    check_out: str
    has_breakfast: bool
    has_lunch: bool
    has_dinner: bool
    county_ids: Annotated[list[int], merge_unique_ids]
    district_ids: Annotated[list[int], merge_unique_ids]
    adults: int
    children: int
    hotel_group_types: str  # 字符串類型，與parser_agent保持一致
    hotel_keyword: str
    plan_keyword: str
    special_requirements: Annotated[list[str], merge_unique_ids]
    supplies: Annotated[list[str], merge_unique_ids]
    hotel_search_results: Annotated[list[dict[str, Any]], merge_hotel_results]
    fuzzy_search_results: Annotated[list[dict[str, Any]], merge_hotel_results]
    plan_search_results: Annotated[list[dict[str, Any]], merge_plan_results]
    response: dict[str, Any]
    text_response: str
    error: str | None


class HotelRecommendationWorkflow:
    """旅館推薦系統工作流"""

    def __init__(self):
        """初始化所有agents和工作流圖"""
        # 初始化所有agents
        # 使用基礎解析器替代尚未實現的文本實體解析器
        # self.text_entity_parser = TextEntityParserAgent()
        self.budget_parser = BudgetParserAgent()
        self.date_parser = DateParserAgent()
        self.geo_parser = GeoParserAgent()
        self.food_req_parser = FoodReqParserAgent()
        self.guest_parser = GuestParserAgent()
        self.hotel_type_parser = HotelTypeParserAgent()
        self.keyword_parser = KeywordParserAgent()
        self.special_req_parser = SpecialReqParserAgent()
        self.supply_parser = SupplyParserAgent()

        self.hotel_search = HotelSearchAgent()
        self.hotel_search_fuzzy = HotelSearchFuzzyAgent()
        self.hotel_search_plan = HotelSearchPlanAgent()

        self.response_generator = ResponseGeneratorAgent()

        self.opencc = OpenCC("s2twp")

        # 創建工作流圖
        self.workflow = self._create_workflow()
        logger.info("工作流初始化完成")

    def _create_workflow(self) -> StateGraph:
        """
        創建LangGraph工作流
        """
        # 創建狀態圖，使用定義的狀態類型
        builder = StateGraph(HotelRecommendationState)

        # 創建節點包裝函數，處理狀態更新
        def node_wrapper(func):
            """包裝節點函數，處理狀態更新"""

            @wraps(func)
            async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
                try:
                    # 記錄節點名稱和輸入狀態
                    function_name = func.__qualname__
                    logger.debug(f"節點執行開始: {function_name}")
                    logger.debug(f"節點輸入狀態: {state}")

                    # 對於解析器，只傳遞查詢字符串
                    if func.__qualname__.endswith("process_query"):
                        # 提取查詢字符串
                        query = state.get("query", "")
                        # 調用解析器函數
                        result = await func(query, {})

                        # 特殊處理某些解析器的結果
                        if "dates" in result:
                            # 日期解析器返回的是 {"dates": {"check_in": "...", "check_out": "..."}}
                            # 需要將 check_in 和 check_out 提取到 state 的頂層
                            dates = result.pop("dates", {})
                            if "check_in" in dates:
                                result["check_in"] = dates["check_in"]
                            if "check_out" in dates:
                                result["check_out"] = dates["check_out"]

                        if "amount" in result:
                            # 預算解析器返回的是 {"amount": 5000}
                            # 需要將 amount 映射到 budget
                            amount = result.pop("amount", None)
                            if amount is not None:
                                result["budget"] = amount

                        if "guests" in result:
                            # 人數解析器返回的是 {"guests": {"adults": 2, "children": 1}}
                            # 需要將 adults 和 children 提取到 state 的頂層
                            guests = result.pop("guests", {})
                            if "adults" in guests:
                                result["adults"] = guests["adults"]
                            if "children" in guests:
                                result["children"] = guests["children"]

                        # 將結果合併回狀態
                        merged_state = dict_merge(state, result)
                        logger.debug(f"節點執行結束: {function_name}")
                        logger.debug(f"節點輸出狀態: {merged_state}")
                        return merged_state

                    # 對於搜索代理和其他函數，傳遞整個狀態
                    result = await func(state)

                    # 確保搜索結果能夠正確合併回狀態
                    if isinstance(result, dict):
                        # 檢查是否有hotel_search_results等關鍵字段
                        for key in ["hotel_search_results", "fuzzy_search_results", "plan_search_results"]:
                            if key in result:
                                # 直接將結果賦值給狀態，不考慮結果數量
                                state[key] = result[key]
                                results_count = len(state[key]) if isinstance(state[key], list) else 0
                                logger.debug(f"節點 {function_name} 返回了 {key}: {results_count} 個結果")
                                logger.debug(f"已將 {key} 結果合併到狀態中，共 {results_count} 個")

                        # 合併結果到狀態
                        merged_state = dict_merge(state, result)
                        logger.debug(f"合併搜索結果到狀態: {merged_state}")
                        logger.debug(f"節點執行結束: {function_name}")
                        logger.debug(f"節點輸出狀態: {merged_state}")
                        return merged_state

                    # 如果結果不是字典，直接返回原始狀態
                    logger.debug(f"節點執行結束: {function_name}")
                    logger.debug(f"節點輸出狀態: {state}")
                    return state
                except Exception as e:
                    logger.error(f"節點執行錯誤: {e}")
                    # 發生錯誤時，返回原始狀態
                    return state

            return wrapped

        # 添加所有節點 - 使用 process_query 而不是 process
        # builder.add_node("text_entity_parser", node_wrapper(self.text_entity_parser.process_query))
        builder.add_node("budget_parser", node_wrapper(self.budget_parser.process_query))
        builder.add_node("date_parser", node_wrapper(self.date_parser.process_query))
        builder.add_node("geo_parser", node_wrapper(self.geo_parser.process_query))
        builder.add_node("food_req_parser", node_wrapper(self.food_req_parser.process_query))
        builder.add_node("guest_parser", node_wrapper(self.guest_parser.process_query))
        builder.add_node("hotel_type_parser", node_wrapper(self.hotel_type_parser.process_query))
        builder.add_node("keyword_parser", node_wrapper(self.keyword_parser.process_query))
        builder.add_node("special_req_parser", node_wrapper(self.special_req_parser.process_query))
        builder.add_node("supply_parser", node_wrapper(self.supply_parser.process_query))

        # 添加搜索節點
        builder.add_node("hotel_search", node_wrapper(self.hotel_search.run))
        builder.add_node("hotel_search_fuzzy", node_wrapper(self.hotel_search_fuzzy.run))
        builder.add_node("hotel_search_plan", node_wrapper(self.hotel_search_plan.run))

        # 添加回應生成節點
        builder.add_node("response_generator", node_wrapper(self.response_generator._process))

        # 添加一個路由節點
        def search_stage_router_node(state):
            # 檢查解析結果，記錄日誌
            logger.info("進入搜索階段路由節點")
            logger.debug(f"解析結果: {state}")
            return state

        builder.add_node("search_stage", search_stage_router_node)

        # 設置起始節點
        builder.set_entry_point("budget_parser")

        # 連接解析節點 - 線性流程，避免並發更新問題
        builder.add_edge("budget_parser", "date_parser")
        builder.add_edge("date_parser", "geo_parser")
        builder.add_edge("geo_parser", "food_req_parser")
        builder.add_edge("food_req_parser", "guest_parser")
        builder.add_edge("guest_parser", "hotel_type_parser")
        builder.add_edge("hotel_type_parser", "keyword_parser")
        builder.add_edge("keyword_parser", "special_req_parser")
        builder.add_edge("special_req_parser", "supply_parser")

        # 從供應解析器到搜索階段
        builder.add_edge("supply_parser", "search_stage")

        # 搜索階段 - 決定執行哪個搜索節點
        def search_stage_router(state):
            # 檢查是否有錯誤
            if state.get("error"):
                logger.error(f"工作流執行錯誤: {state['error']}")
                return "response_generator"

            # 輸出 state 中的內容，用於調試
            logger.debug(f"搜索階段路由節點收到的狀態: {state}")

            # 檢查基本搜索條件
            geo_ready = "county_ids" in state or "district_ids" in state
            date_ready = "check_in" in state and "check_out" in state
            guest_ready = "adults" in state

            # 輸出搜索條件是否滿足
            logger.debug(f"搜索條件: geo_ready={geo_ready}, date_ready={date_ready}, guest_ready={guest_ready}")
            logger.debug(f"county_ids: {state.get('county_ids')}, district_ids: {state.get('district_ids')}")
            logger.debug(f"check_in: {state.get('check_in')}, check_out: {state.get('check_out')}")
            logger.debug(f"adults: {state.get('adults')}")

            # 所有基本參數都存在，執行基本搜索
            if geo_ready and date_ready and guest_ready:
                logger.info("執行基本酒店搜索")
                return "hotel_search"

            # 檢查關鍵字搜索條件
            if state.get("hotel_keyword"):
                # 將 hotel_keyword 映射到 hotel_name，以便 hotel_search_fuzzy_agent 使用
                state["hotel_name"] = state["hotel_keyword"]

                # 如果同時有日期信息，執行方案搜索
                if date_ready:
                    logger.info("執行酒店方案搜索")
                    return "hotel_search_plan"
                # 否則執行模糊搜索
                logger.info("執行酒店模糊搜索")
                return "hotel_search_fuzzy"

            # 如果沒有任何搜索條件滿足，直接跳到回應生成
            logger.warning("無足夠搜索條件，直接生成預設回應")
            return "response_generator"

        # 添加搜索階段路由
        builder.add_conditional_edges("search_stage", search_stage_router)

        # 搜索結果處理 - 確保不論搜索結果如何都能生成回應
        def search_result_check(state):
            if state.get("hotel_search_results"):
                logger.info(f"找到 {len(state['hotel_search_results'])} 個酒店")
                # 檢查是否有關鍵字，確定是否需要模糊搜索
                if state.get("hotel_keyword"):
                    return "hotel_search_fuzzy"
            return "response_generator"

        def fuzzy_search_result_check(state):
            if state.get("fuzzy_search_results"):
                logger.info(f"模糊搜索找到 {len(state['fuzzy_search_results'])} 個酒店")
                # 檢查是否有日期信息，確定是否需要方案搜索
                if "check_in" in state and "check_out" in state:
                    return "hotel_search_plan"
            return "response_generator"

        # 添加搜索結果處理路由
        builder.add_conditional_edges("hotel_search", search_result_check)
        builder.add_conditional_edges("hotel_search_fuzzy", fuzzy_search_result_check)

        # 方案搜索結束後到回應生成
        builder.add_edge("hotel_search_plan", "response_generator")

        # 設置終點
        builder.add_edge("response_generator", END)

        # 編譯工作流
        return builder.compile()

    async def run(self, query: str) -> dict:
        """
        運行工作流
        """
        logger.info(f"開始處理查詢: {query}")

        # 初始狀態
        initial_state = {
            "query": self.opencc.convert(query),
            "query_original": query,
            "timestamp": datetime.now().isoformat(),
            # 初始化空列表和字典，避免None值
            "county_ids": [],
            "district_ids": [],
            "hotel_search_results": [],
            "fuzzy_search_results": [],
            "plan_search_results": [],
            "special_requirements": [],
            "supplies": [],
        }

        # 執行工作流
        try:
            result = await self.workflow.ainvoke(initial_state)
            logger.info("工作流執行完成")
            return result
        except Exception as e:
            logger.error(f"工作流執行失敗: {e}")
            # 返回錯誤信息
            return {"error": str(e), "text_response": "很抱歉，處理您的查詢時發生錯誤。請稍後再試。"}


# 創建工作流實例（單例模式）
hotel_recommendation_workflow = HotelRecommendationWorkflow()


# 添加 run_workflow 函數，作為 hotel_recommendation_workflow.run 的包裝函數
async def run_workflow(data: dict) -> dict:
    """
    運行工作流的包裝函數

    參數:
        data (dict): 包含用戶查詢和上下文信息的字典
            - user_query (str): 用戶查詢
            - context (dict): 上下文信息
            - conversation_id (str): 對話ID

    返回:
        dict: 工作流運行結果
    """
    logger.info(f"處理用戶查詢: {data.get('user_query', '')}")

    # 調用工作流執行
    try:
        result = await hotel_recommendation_workflow.run(data.get("user_query", ""))
        return result
    except Exception as e:
        logger.error(f"工作流執行失敗: {e}")
        return {"error": str(e), "text_response": "很抱歉，處理您的查詢時發生錯誤。請稍後再試。"}
