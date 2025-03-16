import asyncio
import copy
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger
from opencc import OpenCC
from typing_extensions import Annotated

# 引入旅館推薦生成Agent
from src.agents.generators.hotel_recommendation_agent import HotelRecommendationAgent
from src.agents.generators.response_generator_agent import ResponseGeneratorAgent

# 導入所有搜索 agents
from src.agents.search.hotel_search_agent import HotelSearchAgent
from src.agents.search.hotel_search_fuzzy_agent import HotelSearchFuzzyAgent
from src.agents.search.hotel_search_plan_agent import HotelSearchPlanAgent
from src.web.websocket import ws_manager


# 自定義merge函數用於合併字典
def dict_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """合併兩個字典"""
    result = dict1.copy()
    result.update(dict2)
    return result


# 合併兩個response對象，後者優先
def merge_response(response1: dict[str, Any] | None, response2: dict[str, Any] | None) -> dict[str, Any] | None:
    """合併兩個回應對象，如果有衝突，優先使用第二個回應"""
    if response1 is None:
        return response2
    if response2 is None:
        return response1

    # 深度拷貝避免修改原始對象
    result = copy.deepcopy(response1)
    # 使用第二個response更新第一個
    result.update(response2)
    return result


# 合併兩個文本回應，連接它們並用換行符分隔
def merge_text_response(text1: str, text2: str) -> str:
    """合併兩個文本回應，使用換行符分隔"""
    if not text1:
        return text2
    if not text2:
        return text1
    return f"{text1}\n{text2}"


# 合併兩個列表，去除重複的旅館
def merge_hotel_results(list1: list[dict[str, Any]], list2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合併旅館搜索結果，去除重複項"""
    result = list1.copy()
    existing_ids = {item.get("id") for item in result if "id" in item}

    for item in list2:
        if "id" in item and item["id"] not in existing_ids:
            result.append(item)
            existing_ids.add(item["id"])

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


# 合併兩個字符串，如果兩者都有值，保留新的
def merge_keep_last(
    any1: str | float | bool | None, any2: str | float | bool | None
) -> str | int | float | bool | None:
    """合併兩個字符串，優先採用非空值"""
    return any2 if any2 is None else any1


# 合併兩個數字，保留較大值
def merge_max_int(n1: int | None, n2: int | None) -> int | None:
    """合併兩個整數，取較大值"""
    if n1 is None:
        return n2
    if n2 is None:
        return n1
    return max(n1, n2)


# 合併兩個數字，保留較小值
def merge_min_int(n1: int | None, n2: int | None) -> int | None:
    """合併兩個整數，取較小值"""
    if n1 is None:
        return n2
    if n2 is None:
        return n1
    return min(n1, n2)


def merge_keep_first(
    any1: str | float | bool | None, any2: str | float | bool | None
) -> str | int | float | bool | None:
    """合併兩個任意類型，有任一為True則結果為True"""
    return any1 if any1 is not None else any2


# 合併兩個布爾值，有任一為True則為True
def merge_bool_or(b1: bool, b2: bool) -> bool:
    """合併兩個布爾值，有任一為True則結果為True"""
    return b1 or b2


# 合併兩個布爾值，兩者都為True才為True
def merge_bool_and(b1: bool, b2: bool) -> bool:
    """合併兩個布爾值，兩者都為True才結果為True"""
    return b1 and b2


def merge_keep_not_none(any1: str, any2: str) -> str:
    """合併兩個任意類型，有任一為None則結果為None"""
    return any1 or any2


# 定義狀態類型，為多節點並行更新的字段添加合併邏輯
class HotelRecommendationState(TypedDict, total=False):
    """旅館推薦工作流狀態定義"""

    # 基本查詢信息
    query: Annotated[str, merge_keep_not_none]  # 繁體中文轉換後的查詢
    query_original: Annotated[str, merge_keep_not_none]  # 原始查詢字符串
    user_query: Annotated[str, merge_keep_not_none]  # 用戶輸入的原始查詢
    conversation_id: Annotated[str, merge_keep_not_none]  # 會話ID，用於WebSocket通信
    timestamp: Annotated[str, merge_keep_not_none]  # 查詢時間戳

    # 旅館搜索參數
    check_in: Annotated[str, merge_keep_last]  # 入住日期
    check_out: Annotated[str, merge_keep_last]  # 退房日期
    lowest_price: Annotated[int, merge_min_int]  # 最低價格
    highest_price: Annotated[int, merge_max_int]  # 最高價格
    adults: Annotated[int, merge_max_int]  # 成人人數
    children: Annotated[int, merge_max_int]  # 兒童人數
    county_ids: Annotated[list[int], merge_unique_ids]  # 縣市ID
    district_ids: Annotated[list[int], merge_unique_ids]  # 地區ID

    # 額外旅館偏好
    has_breakfast: Annotated[bool, merge_bool_or]  # 是否需要早餐
    has_lunch: Annotated[bool, merge_bool_or]  # 是否需要午餐
    has_dinner: Annotated[bool, merge_bool_or]  # 是否需要晚餐
    hotel_group_types: Annotated[str, merge_keep_last]  # 旅館類型
    hotel_keyword: Annotated[str, merge_keep_last]  # 旅館關鍵字
    plan_keyword: Annotated[str, merge_keep_last]  # 方案關鍵字
    special_requirements: Annotated[list[str], merge_unique_ids]  # 特殊需求
    supplies: Annotated[list[str], merge_unique_ids]  # 設施需求

    # 搜索結果
    hotel_search_results: Annotated[list[dict[str, Any]], merge_hotel_results]  # 旅館搜索結果
    fuzzy_search_results: Annotated[list[dict[str, Any]], merge_hotel_results]  # 模糊搜索結果
    plan_search_results: Annotated[list[dict[str, Any]], merge_plan_results]  # 方案搜索結果

    # 回應結果
    response: Annotated[dict[str, Any], merge_response]  # 結構化回應
    text_response: Annotated[str, merge_text_response]  # 文本回應
    error: str | None  # 錯誤信息

    # 解析器完成狀態
    budget_parsed: Annotated[bool, merge_bool_or]  # 預算解析完成
    date_parsed: Annotated[bool, merge_bool_or]  # 日期解析完成
    geo_parsed: Annotated[bool, merge_bool_or]  # 地理位置解析完成
    food_req_parsed: Annotated[bool, merge_bool_or]  # 餐飲需求解析完成
    guest_parsed: Annotated[bool, merge_bool_or]  # 客人人數解析完成
    hotel_type_parsed: Annotated[bool, merge_bool_or]  # 旅館類型解析完成
    keyword_parsed: Annotated[bool, merge_bool_or]  # 關鍵字解析完成
    special_req_parsed: Annotated[bool, merge_bool_or]  # 特殊需求解析完成
    supply_parsed: Annotated[bool, merge_bool_or]  # 設施需求解析完成

    # 搜索完成狀態
    hotel_search_done: Annotated[bool, merge_bool_or]  # 旅館搜索完成
    fuzzy_search_done: Annotated[bool, merge_bool_or]  # 模糊搜索完成
    plan_search_done: Annotated[bool, merge_bool_or]  # 方案搜索完成

    # 上下文資訊
    context: Annotated[dict[str, Any], merge_keep_last]  # 上下文信息


class HotelRecommendationWorkflow:
    """旅館推薦系統工作流"""

    def __init__(self):
        """初始化所有agents和工作流圖"""
        # 從 instances.py 導入解析器延遲加載器
        from src.agents.parsers.instances import parsers

        # 使用延遲加載器獲取解析器實例
        self.budget_parser = parsers.budget_parser_agent
        self.date_parser = parsers.date_parser_agent
        self.geo_parser = parsers.geo_parser_agent
        self.food_req_parser = parsers.food_req_parser_agent
        self.guest_parser = parsers.guest_parser_agent
        self.hotel_type_parser = parsers.hotel_type_parser_agent
        self.keyword_parser = parsers.keyword_parser_agent
        self.special_req_parser = parsers.special_req_parser_agent
        self.supply_parser = parsers.supply_parser_agent

        self.hotel_search = HotelSearchAgent()
        self.hotel_search_fuzzy = HotelSearchFuzzyAgent()
        self.hotel_search_plan = HotelSearchPlanAgent()

        self.response_generator = ResponseGeneratorAgent()
        # 新增旅館推薦生成Agent
        self.hotel_recommendation = HotelRecommendationAgent()

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
                    agent_class = func.__self__.__class__
                    function_name = agent_class.__name__
                    logger.debug(f"節點執行開始: {function_name}")
                    logger.debug(f"節點輸入狀態: {str(state)[:50]}")

                    # 根據節點類型選擇處理方式
                    if function_name.lower().endswith("parseragent"):
                        # 解析器節點
                        return await _handle_parser_node(func, state)
                    if function_name.lower().endswith("searchagent"):
                        # 搜索節點
                        return await _handle_search_node(func, state)
                    if function_name.lower() == "responsegeneratoragent":
                        # 回應生成節點
                        return await _handle_search_node(func, state)
                    # 其他節點，預設為搜索節點處理
                    return await _handle_search_node(func, state)

                except Exception as e:
                    logger.error(f"節點執行錯誤: {e}")
                    # 發生錯誤時，返回原始狀態
                    return state

            async def _handle_parser_node(func, state: dict[str, Any]) -> dict[str, Any]:
                # 提取查詢字符串
                query = state.get("query", "")
                # 包裝查詢到輸入狀態字典
                parser_state = {"query": query}
                # 調用解析器函數，傳入狀態字典
                result = await func(parser_state)

                # 特殊處理解析器結果
                if "dates" in result:
                    # 處理日期解析結果
                    dates = result.pop("dates", {})
                    if "check_in" in dates:
                        result["check_in"] = dates["check_in"]
                    if "check_out" in dates:
                        result["check_out"] = dates["check_out"]

                if "amount" in result:
                    # 處理預算解析結果
                    amount = result.pop("amount", None)
                    if amount is not None:
                        result["lowest_price"] = amount
                        result["highest_price"] = amount * 2  # 默認上限為下限的兩倍

                if "guests" in result:
                    # 處理人數解析結果
                    guests = result.pop("guests", {})
                    if "adults" in guests:
                        result["adults"] = guests["adults"]
                    if "children" in guests:
                        result["children"] = guests["children"]

                # 標記該解析器已完成
                parser_name = func.__self__.__class__.__name__.lower()
                parser_type = ""

                if parser_name == "budgetparseragent":
                    result["budget_parsed"] = True
                    parser_type = "預算解析器"
                elif parser_name == "dateparseragent":
                    result["date_parsed"] = True
                    parser_type = "日期解析器"
                elif parser_name == "geoparseragent":
                    result["geo_parsed"] = True
                    parser_type = "地理解析器"
                elif parser_name == "foodreqparseragent":
                    result["food_req_parsed"] = True
                    parser_type = "餐飲需求解析器"
                elif parser_name == "guestparseragent":
                    result["guest_parsed"] = True
                    parser_type = "旅客解析器"
                elif parser_name == "hoteltypeparseragent":
                    result["hotel_type_parsed"] = True
                    parser_type = "旅館類型解析器"
                elif parser_name == "keywordparseragent":
                    result["keyword_parsed"] = True
                    parser_type = "關鍵字解析器"
                elif parser_name == "specialreqparseragent":
                    result["special_req_parsed"] = True
                    parser_type = "特殊需求解析器"
                elif parser_name == "supplyparseragent":
                    result["supply_parsed"] = True
                    parser_type = "設施解析器"

                # 加入日誌以便調試
                logger.debug(f"解析器名稱: {parser_name}, 類型: {parser_type}")

                # 將結果合併回狀態
                merged_state = dict_merge(state, result)
                logger.debug(f"節點執行結束: {parser_name}")
                logger.debug(f"節點輸出狀態: {str(merged_state)[:30]}")

                # 發送解析結果通知
                if parser_type and state.get("conversation_id"):
                    await _send_agent_progress(state["conversation_id"], parser_type, result)

                return merged_state

            async def _handle_search_node(func, state: dict[str, Any]) -> dict[str, Any]:
                # 調用搜索函數
                result = await func(state)

                # 識別節點類型
                agent_name = func.__self__.__class__.__name__.lower()
                searcher_type = ""
                results_key = ""

                # 根據 agent 類型標記搜索完成狀態
                if agent_name == "hotelsearchagent":
                    result["hotel_search_done"] = True
                    searcher_type = "旅館搜索"
                    results_key = "hotel_search_results"
                elif agent_name == "hotelsearchfuzzyagent":
                    result["fuzzy_search_done"] = True
                    searcher_type = "旅館模糊搜索"
                    results_key = "fuzzy_search_results"
                elif agent_name == "hotelsearchplanagent":
                    result["plan_search_done"] = True
                    searcher_type = "旅館方案搜索"
                    results_key = "plan_search_results"
                elif agent_name == "responsegeneratoragent":
                    searcher_type = "回應生成"

                # 將結果合併回狀態
                merged_state = dict_merge(state, result)

                # 發送搜索結果通知
                if searcher_type and state.get("conversation_id"):
                    await _send_agent_progress(state["conversation_id"], searcher_type, result)

                # 搜索完成後，處理搜索結果
                if searcher_type in ["旅館搜索", "旅館模糊搜索", "旅館方案搜索"] and results_key in result:
                    _process_search_results(results_key, result, merged_state, agent_name)

                logger.debug(f"節點執行結束: {agent_name}")
                logger.debug(f"節點輸出狀態: {str(merged_state)[:30]}")
                return merged_state

            async def _send_agent_progress(conversation_id: str, agent_type: str, result: dict) -> None:
                """發送解析進度通知"""
                try:
                    # 檢查是否有特定類型的結果
                    message = f"{agent_type}已完成"
                    details = {}

                    if "check_in" in result and "check_out" in result:
                        details["日期"] = f"{result['check_in']} 到 {result['check_out']}"

                    if result.get("county_ids"):
                        details["地點"] = f"縣市ID: {result['county_ids']}"

                    if result.get("adults"):
                        guests = f"{result['adults']}成人"
                        if result.get("children"):
                            guests += f", {result['children']}兒童"
                        details["人數"] = guests

                    if "lowest_price" in result and result["lowest_price"] > 0:
                        details["預算"] = (
                            f"{result['lowest_price']} ~ {result.get('highest_price', result['lowest_price'])}"
                        )

                    if "hotel_search_results" in result and isinstance(result["hotel_search_results"], list):
                        details["搜索結果"] = f"找到 {len(result['hotel_search_results'])} 間旅館"

                    if "fuzzy_search_results" in result and isinstance(result["fuzzy_search_results"], list):
                        details["模糊搜索結果"] = f"找到 {len(result['fuzzy_search_results'])} 間旅館"

                    if "plan_search_results" in result and isinstance(result["plan_search_results"], list):
                        details["方案搜索結果"] = f"找到 {len(result['plan_search_results'])} 個方案"

                    if "text_response" in result:
                        message = "處理完成"

                    # 添加細節到消息中
                    if details:
                        detail_str = "，".join([f"{k}: {v}" for k, v in details.items()])
                        message += f"（{detail_str}）"

                    # 發送進度通知到前端
                    await ws_manager.broadcast_chat_message(
                        conversation_id,
                        {
                            "role": "system",
                            "content": message,
                            "timestamp": asyncio.get_event_loop().time(),
                            "agent_type": agent_type,
                            "details": details,
                        },
                    )
                except Exception as e:
                    logger.error(f"發送進度通知失敗: {e}")

            def _process_search_results(key: str, result: dict, state: dict, function_name: str) -> None:
                """處理搜索結果並更新狀態"""
                # 檢查結果是否為有效列表
                if isinstance(result[key], list) and result[key]:
                    # 有效列表且非空，才更新狀態
                    state[key] = result[key]
                    results_count = len(state[key])
                    logger.info(f"節點 {function_name} 返回了 {key}: {results_count} 個結果")
                    logger.debug(f"已將 {key} 結果合併到狀態中，共 {results_count} 個")

                    # 檢查前三個結果的名稱
                    if results_count > 0 and all(isinstance(item, dict) for item in state[key][:3]):
                        sample_names = [item.get("name", "未知") for item in state[key][:3] if isinstance(item, dict)]
                        logger.info(f"{key} 結果示例: {', '.join(sample_names)}")
                elif isinstance(result[key], list) and not result[key]:
                    # 空列表，且狀態中不存在該鍵，才初始化為空列表
                    if key not in state:
                        state[key] = []
                    logger.warning(f"節點 {function_name} 返回了空的 {key}")
                # 否則保留原有的結果
                elif key in state and isinstance(state[key], list) and state[key]:
                    logger.info(f"保留原有的 {key}，共 {len(state[key])} 個結果")
                # 其他情況
                else:
                    logger.debug(f"處理 {key}: 結果類型 {type(result[key])}，狀態中已有 {key in state}")

            return wrapped

        # 添加所有節點 - 使用 process 方法
        builder.add_node("budget_parser", node_wrapper(self.budget_parser.process))
        builder.add_node("date_parser", node_wrapper(self.date_parser.process))
        builder.add_node("geo_parser", node_wrapper(self.geo_parser.process))
        builder.add_node("food_req_parser", node_wrapper(self.food_req_parser.process))
        builder.add_node("guest_parser", node_wrapper(self.guest_parser.process))
        builder.add_node("hotel_type_parser", node_wrapper(self.hotel_type_parser.process))
        builder.add_node("keyword_parser", node_wrapper(self.keyword_parser.process))
        builder.add_node("special_req_parser", node_wrapper(self.special_req_parser.process))
        builder.add_node("supply_parser", node_wrapper(self.supply_parser.process))

        # 添加搜索節點
        builder.add_node("hotel_search", node_wrapper(self.hotel_search.process))
        builder.add_node("hotel_search_fuzzy", node_wrapper(self.hotel_search_fuzzy.process))
        builder.add_node("hotel_search_plan", node_wrapper(self.hotel_search_plan.process))

        # 添加搜索結果匯總節點
        def search_results_aggregator(state):
            logger.info("匯總搜索結果")
            # 檢查是否有搜索結果
            has_search_results = (
                bool(state.get("hotel_search_results"))
                or bool(state.get("fuzzy_search_results"))
                or bool(state.get("plan_search_results"))
            )
            logger.info(
                f"搜索結果狀態: hotel_search={bool(state.get('hotel_search_results'))}, "
                f"fuzzy_search={bool(state.get('fuzzy_search_results'))}, "
                f"plan_search={bool(state.get('plan_search_results'))}"
            )

            if not has_search_results:
                logger.warning("未找到任何搜索結果")

            return state

        builder.add_node("search_results_aggregator", search_results_aggregator)

        # 添加數據處理節點
        builder.add_node("response_generator", node_wrapper(self.response_generator.process))
        # 添加推薦生成節點
        builder.add_node("hotel_recommendation", node_wrapper(self.hotel_recommendation.process))

        # 設置起始節點 - 並行執行所有解析器
        builder.set_entry_point("parse_router")

        # 解析路由節點 - 分發到各個解析器
        def parse_router(state):
            logger.info("解析階段路由")
            logger.debug(f"當前狀態: {str(state)[:50]}")
            # 不返回列表，而是返回原始狀態字典
            return state

        # 添加解析路由節點
        builder.add_node("parse_router", parse_router)

        # 設置從解析路由到各個解析器的邊 - 使用條件邊替代直接邊
        def parse_route_selector(state):
            # 返回所有解析器節點名稱
            return [
                "budget_parser",
                "date_parser",
                "geo_parser",
                "food_req_parser",
                "guest_parser",
                "hotel_type_parser",
                "keyword_parser",
                "special_req_parser",
                "supply_parser",
            ]

        # 使用條件邊連接parse_router到所有解析器
        builder.add_conditional_edges("parse_router", parse_route_selector)

        # 搜索路由函數 - 根據解析結果決定執行哪些搜索
        def search_router(state):
            logger.info("搜索階段路由")
            # 返回原始狀態，而不是目標節點列表
            return state

        # 添加搜索階段節點
        builder.add_node("search_router", search_router)

        # 從搜索路由到各個搜索節點的條件選擇
        def search_route_selector(state):
            to_execute = []

            # 檢查是否有錯誤
            if state.get("error"):
                logger.error(f"工作流執行錯誤: {state['error']}")
                return ["response_generator"]

            # 獲取當前搜索重試次數，預設為0
            retry_count = state.get("search_retry_count", 0)
            # 設置最大重試次數
            MAX_SEARCH_RETRIES = 2

            # 檢查是否已達到最大重試次數，如果是則直接進入結果匯總階段
            if retry_count >= MAX_SEARCH_RETRIES:
                logger.warning(f"已達到最大重試次數 ({MAX_SEARCH_RETRIES})，不再嘗試搜索")
                state["message"] = f"未找到完全符合條件的旅館，已嘗試 {retry_count} 次。以下是最接近的結果。"
                return ["search_results_aggregator"]

            # 檢查關鍵字搜索條件：是否有關鍵字且未執行過模糊搜索
            keyword_ready = state.get("keyword_parsed", False) and state.get("hotel_keyword")
            if keyword_ready and not state.get("fuzzy_search_done", False):
                # 將 hotel_keyword 映射到 hotel_name，以便 hotel_search_fuzzy_agent 使用
                state["hotel_name"] = state.get("hotel_keyword", "")
                logger.info("添加旅館模糊搜索到執行清單")
                to_execute.append("hotel_search_fuzzy")

            # 檢查方案搜索條件：是否有關鍵字和日期且未執行過方案搜索
            plan_search_ready = (
                keyword_ready
                and state.get("date_parsed", False)
                and "check_in" in state
                and state["check_in"]
                and "check_out" in state
                and state["check_out"]
                and not state.get("plan_search_done", False)
            )
            if plan_search_ready:
                logger.info("添加旅館方案搜索到執行清單")
                to_execute.append("hotel_search_plan")

            # 檢查是否有基本的地理位置信息，確保可以執行基本搜索
            has_geo_data = False

            # 檢查來源於各種可能的地理位置資訊
            if state.get("geo_data") and state.get("geo_data", {}).get("county_id"):
                has_geo_data = True
                # 將基本搜索參數加入到狀態中
                county_id = state.get("geo_data", {}).get("county_id", 0)
                logger.info(f"從 geo_data 獲取縣市ID: {county_id}")
            elif state.get("destination", {}).get("county"):
                county_id = state.get("destination", {}).get("county")
                has_geo_data = bool(county_id)
                logger.info(f"從 destination 獲取縣市ID: {county_id}")
            elif state.get("county_ids"):
                county_id = state.get("county_ids", [0])[0]
                has_geo_data = bool(county_id)
                logger.info(f"從 county_ids 獲取縣市ID: {county_id}")
            else:
                logger.warning("缺少縣市ID，無法執行基本旅館搜索")

            # 如果有地理位置資訊，設置基本搜索參數
            if has_geo_data:
                # 設置基本搜索參數
                search_params = {
                    "county_id": county_id,
                    "check_in": state.get("check_in", datetime.now().strftime("%Y-%m-%d")),
                    "check_out": state.get("check_out", (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")),
                    "adults": state.get("adults", 2),
                    "children": state.get("children", 0),
                    "lowest_price": state.get("lowest_price", 0),
                    "highest_price": state.get("highest_price", 0),
                }

                # 添加到狀態中
                state["hotel_search_params"] = search_params
                logger.info(f"已準備基本搜索參數: {search_params}")

            # 輸出搜索條件日誌
            logger.info(
                f"搜索條件: has_geo_data={has_geo_data}, hotel_search_done={state.get('hotel_search_done', False)}"
            )

            # 如果有地理位置信息且還沒有執行過基本搜索，添加到執行清單
            if has_geo_data and not state.get("hotel_search_done", False):
                logger.info("添加基本旅館搜索到執行清單")
                to_execute.append("hotel_search")

            # 如果所有搜索都已完成，或確實沒有任何搜索條件可以執行
            all_searches_done = (
                (state.get("hotel_search_done", False) or not has_geo_data)
                and (state.get("fuzzy_search_done", False) or not keyword_ready)
                and (state.get("plan_search_done", False) or not plan_search_ready)
            )

            # 檢查是否有任何搜索結果
            has_any_results = (
                bool(state.get("hotel_search_results"))
                or bool(state.get("fuzzy_search_results"))
                or bool(state.get("plan_search_results"))
            )

            # 如果所有搜索都已完成，或確實沒有任何搜索條件可以執行
            if all_searches_done or not to_execute:
                # 如果沒有任何搜索結果，且未達到最大重試次數，嘗試放寬條件執行基本搜索
                if not has_any_results and retry_count < MAX_SEARCH_RETRIES:
                    # 增加重試計數
                    state["search_retry_count"] = retry_count + 1
                    logger.warning(
                        f"沒有搜索結果，嘗試放寬條件執行旅館搜索 (重試 {state['search_retry_count']}/{MAX_SEARCH_RETRIES})"
                    )

                    # 如果有任何縣市ID，重置搜索完成標記並執行基本搜索
                    if has_geo_data:
                        # 重置搜索完成標記
                        state["hotel_search_done"] = False
                        logger.info("重試搜索，準備使用放寬條件")
                        return ["hotel_search"]
                    # 沒有任何地理資訊可用，直接進入結果匯總階段
                    logger.info("沒有足夠的搜索條件，進入結果匯總階段")
                    return ["search_results_aggregator"]

                # 如果已經有結果或者已達到最大重試次數，進入結果匯總階段
                if not has_any_results and retry_count >= MAX_SEARCH_RETRIES:
                    state["message"] = f"未找到符合條件的旅館，請嘗試調整搜索條件。(已嘗試 {retry_count} 次)"

                logger.info("所有搜索已完成或達到最大重試次數，進入結果匯總階段")
                return ["search_results_aggregator"]

            logger.info(f"將執行以下搜索節點: {to_execute}")
            return to_execute

        # 將所有解析器連接到搜索路由
        for parser in [
            "budget_parser",
            "date_parser",
            "geo_parser",
            "food_req_parser",
            "guest_parser",
            "hotel_type_parser",
            "keyword_parser",
            "special_req_parser",
            "supply_parser",
        ]:
            builder.add_edge(parser, "search_router")

        # 從搜索路由到各個搜索節點 - 使用條件邊
        builder.add_conditional_edges("search_router", search_route_selector)

        # 將搜索節點連接到搜索結果匯總節點
        for searcher in ["hotel_search", "hotel_search_fuzzy", "hotel_search_plan"]:
            builder.add_edge(searcher, "search_results_aggregator")

        # 添加條件邊檢查函數 - 從搜索節點到路由節點
        def search_to_router_condition(state):
            """
            決定是否需要將搜索節點連回搜索路由進行循環處理。
            僅在有明確需要重新搜索的情況下才返回 True，否則直接進入匯總階段。

            返回:
                list: 如果需要重新搜索則返回 ["search_router"]，否則返回 ["search_results_aggregator"]
            """
            # 獲取重試次數
            retry_count = state.get("search_retry_count", 0)
            max_retries = 2

            # 檢查是否有搜索結果
            has_results = (
                bool(state.get("hotel_search_results"))
                or bool(state.get("fuzzy_search_results"))
                or bool(state.get("plan_search_results"))
            )

            # 只有在未達到最大重試次數且沒有結果的情況下才繼續循環
            if retry_count < max_retries and not has_results:
                # 檢查是否有其他搜索條件可以嘗試
                has_other_search_options = (not state.get("fuzzy_search_done") and state.get("hotel_keyword")) or (
                    not state.get("plan_search_done") and state.get("check_in") and state.get("check_out")
                )

                if has_other_search_options:
                    logger.info(f"搜索未完成且有其他選項可用，重新進入搜索路由 (重試 {retry_count}/{max_retries})")
                    return ["search_router"]

            # 默認進入結果匯總階段
            logger.info("搜索已完成或達到最大重試次數，進入結果匯總階段")
            return ["search_results_aggregator"]

        # 為每個搜索節點添加條件邊
        for searcher in ["hotel_search", "hotel_search_fuzzy", "hotel_search_plan"]:
            # 刪除原有的直接邊
            # builder.add_edge(searcher, "search_router")

            # 添加條件邊 - 修正條件邊設置方式
            builder.add_conditional_edges(searcher, search_to_router_condition)

        # 將結果匯總節點連接到回應生成，改為先連接到response_generator
        builder.add_edge("search_results_aggregator", "response_generator")

        # 將response_generator連接到hotel_recommendation
        builder.add_edge("response_generator", "hotel_recommendation")

        # 將hotel_recommendation連接到終點
        builder.add_edge("hotel_recommendation", END)

        # 編譯工作流
        return builder.compile()

    async def run(self, query: str, conversation_id: str = "", user_query: str = "") -> dict:
        """
        運行工作流

        參數:
            query (str): 用戶查詢字符串（已轉換為繁體）
            conversation_id (str): 對話ID，用於WebSocket通信
            user_query (str): 原始用戶查詢（未轉換）

        返回:
            dict: 工作流運行結果
        """
        logger.info(f"開始處理查詢: {query}")

        # 如果沒有提供原始查詢，則使用轉換後的查詢
        if not user_query:
            user_query = query

        # 初始狀態
        initial_state = {
            # 基本查詢信息
            "query": query,
            "query_original": query,
            "user_query": user_query,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            # 初始化空列表和字典，避免None值
            "county_ids": [],
            "district_ids": [],
            "hotel_search_results": [],
            "fuzzy_search_results": [],
            "plan_search_results": [],
            "special_requirements": [],
            "supplies": [],
            # 初始化數值欄位，避免None值
            "lowest_price": 0,
            "highest_price": 0,
            "adults": 0,
            "children": 0,
            # 初始化布爾欄位，避免None值
            "has_breakfast": False,
            "has_lunch": False,
            "has_dinner": False,
            # 初始化字符串欄位，避免None值
            "hotel_group_types": "",
            "hotel_keyword": "",
            "plan_keyword": "",
            # 初始化解析器完成狀態
            "budget_parsed": False,
            "date_parsed": False,
            "geo_parsed": False,
            "food_req_parsed": False,
            "guest_parsed": False,
            "hotel_type_parsed": False,
            "keyword_parsed": False,
            "special_req_parsed": False,
            "supply_parsed": False,
            # 初始化搜索完成狀態
            "hotel_search_done": False,
            "fuzzy_search_done": False,
            "plan_search_done": False,
            # 上下文信息
            "context": {},
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
async def run_workflow(data: dict | str, progress_callback: callable = None) -> dict:
    """
    運行工作流的包裝函數

    參數:
        data (dict | str): 包含用戶查詢和上下文信息的字典或直接是查詢字符串
            - 如果是字典，應包含:
              - user_query (str): 用戶查詢
              - context (dict): 上下文信息
              - conversation_id (str): 對話ID
            - 如果是字符串，則直接作為用戶查詢
        progress_callback (callable): 進度回調函數，用於報告處理進度

    返回:
        dict: 工作流運行結果
    """
    import asyncio

    # 處理不同類型的輸入
    if isinstance(data, str):
        user_query = data
        conversation_id = ""
        context = {}
    else:
        user_query = data.get("user_query", "")
        conversation_id = data.get("conversation_id", "")
        context = data.get("context", {})

    # 檢查查詢是否為空
    if not user_query:
        logger.error("用戶查詢為空")
        return {"error": "查詢內容為空", "text_response": "請提供查詢內容"}

    # 轉換為繁體中文
    query = hotel_recommendation_workflow.opencc.convert(user_query)
    logger.info(f"處理用戶查詢: {query}, 對話ID: {conversation_id}")

    # 如果有進度回調，報告開始解析查詢
    if progress_callback:
        await progress_callback("parse_query")

    # 設置超時時間（30秒）
    WORKFLOW_TIMEOUT = 30.0

    # 使用asyncio.wait_for添加超時機制
    try:
        # 使用超時機制運行工作流
        result = await asyncio.wait_for(
            hotel_recommendation_workflow.run(query=query, conversation_id=conversation_id, user_query=user_query),
            timeout=WORKFLOW_TIMEOUT,
        )

        # 如果有進度回調，報告處理完成
        if progress_callback:
            await progress_callback("final_response")

        return result
    except TimeoutError:
        logger.error(f"工作流執行超時 ({WORKFLOW_TIMEOUT}秒)")

        # 如果有進度回調，報告超時錯誤
        if progress_callback:
            await progress_callback("error", message=f"處理查詢超時 ({WORKFLOW_TIMEOUT}秒)")

        return {
            "error": f"處理查詢超時 ({WORKFLOW_TIMEOUT}秒)",
            "text_response": "很抱歉，處理您的查詢花費時間過長，請嘗試更簡單的查詢或稍後再試。",
        }
    except Exception as e:
        logger.error(f"工作流執行失敗: {e}")

        # 獲取更詳細的錯誤信息
        import traceback

        error_detail = traceback.format_exc()
        logger.error(f"詳細錯誤信息:\n{error_detail}")

        # 如果有進度回調，報告錯誤
        if progress_callback:
            await progress_callback("error", message=str(e))

        return {
            "error": str(e),
            "text_response": f"很抱歉，處理您的查詢時發生錯誤: {e}",
        }
