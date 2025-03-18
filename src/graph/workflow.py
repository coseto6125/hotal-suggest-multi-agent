# TODO: 錯誤處理節點,可於wrap中做，或是考慮把websocket agent化


import asyncio
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger
from opencc import OpenCC
from typing_extensions import Annotated

# 引入所需的 Agent
from src.agents.generators.hotel_recommendation_agent import HotelRecommendationAgent
from src.agents.generators.response_generator_agent import ResponseGeneratorAgent
from src.agents.search.hotel_search_agent import HotelSearchAgent
from src.agents.search.hotel_search_fuzzy_agent import HotelSearchFuzzyAgent
from src.agents.search.hotel_search_plan_agent import HotelSearchPlanAgent
from src.graph.merge_func import MergeFunc
from src.web.websocket import ws_manager

# ========== 工作流狀態定義 ==========


class HotelRecommendationState(TypedDict, total=False):
    """旅館推薦工作流狀態定義"""

    # 基本查詢信息
    query: Annotated[str, MergeFunc.keep_not_none]  # 繁體中文轉換後的查詢
    query_original: Annotated[str, MergeFunc.keep_not_none]  # 原始查詢字符串
    user_query: Annotated[str, MergeFunc.keep_not_none]  # 用戶輸入的原始查詢
    session_id: Annotated[str, MergeFunc.keep_not_none]  # 會話ID，用於WebSocket通信
    timestamp: Annotated[str, MergeFunc.keep_not_none]  # 查詢時間戳

    # 旅館搜索參數
    check_in: Annotated[str, MergeFunc.keep_not_none]  # 入住日期
    check_out: Annotated[str, MergeFunc.keep_not_none]  # 退房日期
    lowest_price: Annotated[int, MergeFunc.min_int]  # 最低價格
    highest_price: Annotated[int, MergeFunc.max_int]  # 最高價格
    adults: Annotated[int, MergeFunc.max_int]  # 成人人數
    children: Annotated[int, MergeFunc.max_int]  # 兒童人數
    county_ids: Annotated[list[int], MergeFunc.unique_ids]  # 縣市ID
    district_ids: Annotated[list[int], MergeFunc.unique_ids]  # 地區ID
    llm_recommend_hotel: Annotated[list[str], MergeFunc.list_merge]  # LLM推薦的旅館
    llm_recommend_poi: Annotated[list[str], MergeFunc.list_merge]  # LLM推薦的POI

    # 額外旅館偏好
    has_breakfast: Annotated[bool, MergeFunc.bool_or]  # 是否需要早餐
    has_lunch: Annotated[bool, MergeFunc.bool_or]  # 是否需要午餐
    has_dinner: Annotated[bool, MergeFunc.bool_or]  # 是否需要晚餐
    hotel_group_types: Annotated[str, MergeFunc.keep_last]  # 旅館類型
    hotel_keyword: Annotated[str, MergeFunc.keep_last]  # 旅館關鍵字
    plan_keyword: Annotated[str, MergeFunc.keep_last]  # 方案關鍵字
    special_requirements: Annotated[list[str], MergeFunc.unique_ids]  # 特殊需求
    supplies: Annotated[list[str], MergeFunc.unique_ids]  # 設施需求

    # 搜索結果
    hotel_search_results: Annotated[list[dict[str, Any]], MergeFunc.hotel_results]  # 旅館搜索結果
    fuzzy_search_results: Annotated[list[dict[str, Any]], MergeFunc.hotel_results]  # 模糊搜索結果
    plan_search_results: Annotated[list[dict[str, Any]], MergeFunc.plan_results]  # 方案搜索結果

    # 回應結果
    response: Annotated[dict[str, Any], MergeFunc.response]  # 結構化回應
    text_response: Annotated[str, MergeFunc.text_response]  # 文本回應
    error: Annotated[str, MergeFunc.keep_not_none]  # 錯誤信息
    err_msg: Annotated[str, MergeFunc.keep_not_none]  # 錯誤訊息

    # 解析器完成狀態
    budget_parsed: Annotated[bool, MergeFunc.bool_or]  # 預算解析完成
    date_parsed: Annotated[bool, MergeFunc.bool_or]  # 日期解析完成
    geo_parsed: Annotated[bool, MergeFunc.bool_or]  # 地理位置解析完成
    food_req_parsed: Annotated[bool, MergeFunc.bool_or]  # 餐飲需求解析完成
    guest_parsed: Annotated[bool, MergeFunc.bool_or]  # 客人人數解析完成
    hotel_type_parsed: Annotated[bool, MergeFunc.bool_or]  # 旅館類型解析完成
    keyword_parsed: Annotated[bool, MergeFunc.bool_or]  # 關鍵字解析完成
    special_req_parsed: Annotated[bool, MergeFunc.bool_or]  # 特殊需求解析完成
    supply_parsed: Annotated[bool, MergeFunc.bool_or]  # 設施需求解析完成

    # 搜索完成狀態
    hotel_search_done: Annotated[bool, MergeFunc.bool_or]  # 旅館搜索完成
    fuzzy_search_done: Annotated[bool, MergeFunc.bool_or]  # 模糊搜索完成
    plan_search_done: Annotated[bool, MergeFunc.bool_or]  # 方案搜索完成

    # 上下文資訊
    context: Annotated[dict[str, Any], MergeFunc.keep_last]  # 上下文信息


# ========== 工作流核心類 ==========


class HotelRecommendationWorkflow:
    """旅館推薦系統工作流"""

    def __init__(self):
        """初始化所有agents和工作流圖"""
        # 延遲載入解析器
        self._load_parsers()

        # 初始化搜索 agents
        self._init_search_agents()

        # 初始化生成 agents
        self._init_generator_agents()

        # 初始化繁簡體轉換工具
        self.opencc = OpenCC("s2twp")

        # 創建工作流圖
        self.workflow = self._create_workflow()
        logger.info("工作流初始化完成")

        self.parser_types = {
            "budgetparseragent": "預算解析器",
            "dateparseragent": "日期解析器",
            "geoparseragent": "地理解析器",
            "foodreqparseragent": "餐飲需求解析器",
            "guestparseragent": "旅客解析器",
        }

    def _load_parsers(self):
        """載入所有解析器"""
        from src.agents.parsers.instances import parsers

        self.budget_parser = parsers.budget_parser_agent
        self.date_parser = parsers.date_parser_agent
        self.geo_parser = parsers.geo_parser_agent
        self.food_req_parser = parsers.food_req_parser_agent
        self.guest_parser = parsers.guest_parser_agent
        self.hotel_type_parser = parsers.hotel_type_parser_agent
        self.keyword_parser = parsers.keyword_parser_agent
        self.special_req_parser = parsers.special_req_parser_agent
        self.supply_parser = parsers.supply_parser_agent

    def _init_search_agents(self):
        """初始化搜索agents"""
        self.hotel_search = HotelSearchAgent()
        self.hotel_search_fuzzy = HotelSearchFuzzyAgent()
        self.hotel_search_plan = HotelSearchPlanAgent()

    def _init_generator_agents(self):
        """初始化生成agents"""
        # 載入LLM Agent
        from src.agents.generators.llm_agent import llm_agent

        self.llm_agent = llm_agent

        # 初始化回應生成器和旅館推薦器
        self.response_generator = ResponseGeneratorAgent()
        self.hotel_recommendation = HotelRecommendationAgent()

    def _create_workflow(self) -> StateGraph:
        """創建LangGraph工作流"""
        # 建立工作流圖
        builder = StateGraph(HotelRecommendationState)

        # 添加所有節點
        self._add_parser_nodes(builder)
        self._add_search_nodes(builder)
        self._add_aggregator_nodes(builder)
        self._add_generator_nodes(builder)
        # 設置邊和條件
        self._setup_workflow_edges(builder)

        # 添加錯誤處理邊
        def error_handler_condition(state):
            logger.info(f"錯誤處理條件被調用，狀態: {str(state)[:100]}")
            return ["error_handler"] if state.get("error") else ["search_router"]

        for node_name in builder.nodes:
            if "parser" in node_name:
                builder.add_conditional_edges(node_name, error_handler_condition)
        # 編譯工作流
        return builder.compile()

    def _add_parser_nodes(self, builder: StateGraph):
        """添加解析器相關節點"""
        # 添加所有解析器節點
        builder.add_node("budget_parser", self._node_wrapper(self.budget_parser.process))
        builder.add_node("date_parser", self._node_wrapper(self.date_parser.process))
        builder.add_node("geo_parser", self._node_wrapper(self.geo_parser.process))
        builder.add_node("food_req_parser", self._node_wrapper(self.food_req_parser.process))
        builder.add_node("guest_parser", self._node_wrapper(self.guest_parser.process))
        builder.add_node("hotel_type_parser", self._node_wrapper(self.hotel_type_parser.process))
        builder.add_node("keyword_parser", self._node_wrapper(self.keyword_parser.process))
        builder.add_node("special_req_parser", self._node_wrapper(self.special_req_parser.process))
        builder.add_node("supply_parser", self._node_wrapper(self.supply_parser.process))

        # 添加解析路由節點
        def parse_router(state):
            logger.info("解析階段路由")
            logger.debug(f"當前狀態: {str(state)[:50]}")
            return state

        builder.add_node("parse_router", parse_router)

    def _add_search_nodes(self, builder: StateGraph):
        """添加搜索相關節點"""
        # 添加搜索節點
        builder.add_node("hotel_search", self._node_wrapper(self.hotel_search.process))
        builder.add_node("hotel_search_fuzzy", self._node_wrapper(self.hotel_search_fuzzy.process))
        builder.add_node("hotel_search_plan", self._node_wrapper(self.hotel_search_plan.process))

        # 添加搜索路由節點
        def search_router(state):
            logger.info("搜索階段路由")
            return state

        builder.add_node("search_router", search_router)

        # 添加錯誤處理節點
        builder.add_node("error_handler", self._error_handler)

    def _add_aggregator_nodes(self, builder: StateGraph):
        """添加結果匯總節點"""

        def search_results_aggregator(state):
            logger.info("匯總搜索結果")
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

    def _add_generator_nodes(self, builder: StateGraph):
        """添加生成相關節點"""
        # 添加LLM Agent節點
        builder.add_node("llm_agent", self._node_wrapper(self.llm_agent.process))

        # 添加回應生成器和旅館推薦節點
        builder.add_node("response_generator", self._node_wrapper(self.response_generator.process))
        builder.add_node("hotel_recommendation", self._node_wrapper(self.hotel_recommendation.process))

    def _setup_workflow_edges(self, builder: StateGraph):
        """設置工作流的邊和條件"""
        # 設置起始節點
        builder.set_entry_point("parse_router")

        # 設置錯誤處理邊
        builder.add_edge("error_handler", END)

        # 設置解析器邊
        self._setup_parser_edges(builder)

        # 設置搜索節點邊
        self._setup_search_edges(builder)

        # 設置生成節點邊
        self._setup_generator_edges(builder)

    def _setup_parser_edges(self, builder: StateGraph):
        """設置解析階段的邊和條件"""

        # 從解析路由到各個解析器的條件邊
        def parse_route_selector(state):
            # 檢查是否有錯誤
            logger.info(f"解析路由選擇器被調用，狀態: {str(state)[:100]}")
            if state.get("error"):
                logger.error(f"解析階段發現錯誤: {state.get('error')}")
                return ["error_handler"]
            # 返回所有解析器節點列表
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

        builder.add_conditional_edges("parse_router", parse_route_selector)

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

    def _setup_search_edges(self, builder: StateGraph):
        """設置搜索階段的邊和條件"""
        # 從搜索路由到各個搜索節點的條件邊
        builder.add_conditional_edges("search_router", self._search_route_selector)

        # 將搜索節點連接到搜索結果匯總節點
        for searcher in ["hotel_search", "hotel_search_fuzzy", "hotel_search_plan"]:
            builder.add_edge(searcher, "search_results_aggregator")
            # 設置搜索節點到搜索路由的條件邊
            builder.add_conditional_edges(searcher, self._search_to_router_condition)

    def _setup_generator_edges(self, builder: StateGraph):
        """設置生成階段的邊和條件"""
        # 將結果匯總節點連接到LLM Agent
        builder.add_edge("search_results_aggregator", "llm_agent")

        # 將LLM Agent連接到回應生成器
        builder.add_edge("llm_agent", "response_generator")

        # 將response_generator連接到hotel_recommendation
        builder.add_edge("response_generator", "hotel_recommendation")

        # 將hotel_recommendation連接到終點
        builder.add_edge("hotel_recommendation", END)

    def _node_wrapper(self, func):
        """包裝節點函數，處理狀態更新"""

        @wraps(func)
        async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
            try:
                # 獲取節點信息
                agent_class = func.__self__.__class__
                agent_name = agent_class.__name__.lower()
                logger.debug(f"節點執行開始: {agent_name}")

                if error := state.get("error"):
                    logger.warning(f"節點 {agent_name} 被跳過，因為已存在錯誤: {error}")
                    return state
                # 執行節點函數
                result = await func(state)

                # 合併結果到狀態
                merged_state = MergeFunc.dict_merge(state, result)

                # 處理特定類型的節點
                if "parseragent" in agent_name:
                    # 處理解析器節點
                    parser_type = self.parser_types.get(agent_name, "")
                    if parser_type and state.get("session_id"):
                        await self._send_agent_progress(state["session_id"], parser_type, result)
                else:
                    # 處理搜索節點
                    searcher_info = self._get_searcher_info(agent_name, result)
                    if searcher_info["type"] == "旅館推薦生成":
                        # result["llm_recommend_poi"] = ["雀客藏居台北南港", "雀客藏居台北陽明山"]
                        # 確保 merged_state 也有 llm_recommend_poi
                        merged_state["llm_recommend_poi"] += result["llm_recommend_poi"]
                        
                        if merged_state.get("llm_recommend_poi"):
                            merged_state["llm_recommend_poi"] = merged_state["llm_recommend_poi"][:3]
                            logger.info(f"開始處理POI資訊預備，推薦POI: {merged_state['llm_recommend_poi']}")
                            # 使用POISearchAgent處理POI搜索
                            from src.agents.search.poi_search_agent import poi_search_agent

                            # 確認狀態中是否有旅館搜尋結果
                            hotel_results = (
                                merged_state.get("hotel_search_results", [])
                                or merged_state.get("fuzzy_search_results", [])
                                or merged_state.get("plan_search_results", [])
                            )

                            logger.info(
                                f"旅館搜尋結果狀態: hotel_search_results={bool(merged_state.get('hotel_search_results'))}, "
                                f"fuzzy_search_results={bool(merged_state.get('fuzzy_search_results'))}, "
                                f"plan_search_results={bool(merged_state.get('plan_search_results'))}"
                            )

                            if not hotel_results:
                                logger.warning("沒有任何旅館搜尋結果，無法進行 POI 搜索")
                                return merged_state

                            poi_result = await poi_search_agent.process(merged_state)

                            # 合併POI結果到狀態
                            if "poi_results" in poi_result:
                                merged_state["poi_results"] = poi_result["poi_results"]

                            # 如果有地圖圖片，透過WebSocket發送給前端
                            if (
                                "surroundings_map_images" in poi_result
                                and poi_result["surroundings_map_images"]
                                and state.get("session_id")
                            ):
                                await self._send_poi_images(state["session_id"], poi_result["surroundings_map_images"])
                        else:
                            logger.info("沒有LLM推薦的POI，跳過POI資訊預備")
                    elif searcher_info["type"] and state.get("session_id"):
                        await self._send_agent_progress(state["session_id"], searcher_info["type"], result)

                    # 處理搜索結果
                    if (
                        searcher_info["type"] in ["旅館搜索", "旅館模糊搜索", "旅館方案搜索"]
                        and searcher_info["results_key"] in result
                    ):
                        self._process_search_results(searcher_info["results_key"], result, merged_state, agent_name)

                logger.debug(f"節點執行結束: {agent_name}")
                return merged_state

            except Exception as e:
                logger.error(f"節點執行錯誤: {e}")
                return state

        return wrapped

    def _get_searcher_info(self, agent_name: str, result: dict) -> dict:
        """獲取搜索節點的相關信息"""
        searcher_info = {"type": "", "results_key": ""}

        # 根據 agent 類型標記搜索完成狀態
        match agent_name:
            case "hotelsearchagent":
                result["hotel_search_done"] = True
                searcher_info["type"] = "旅館搜索"
                searcher_info["results_key"] = "hotel_search_results"
            case "hotelsearchfuzzyagent":
                result["fuzzy_search_done"] = True
                searcher_info["type"] = "旅館模糊搜索"
                searcher_info["results_key"] = "fuzzy_search_results"
            case "hotelsearchplanagent":
                result["plan_search_done"] = True
                searcher_info["type"] = "旅館方案搜索"
                searcher_info["results_key"] = "plan_search_results"
            case "responsegeneratoragent":
                searcher_info["type"] = "回應生成"
            case "hotelrecommendationagent":
                searcher_info["type"] = "旅館推薦生成"

        return searcher_info

    async def _send_agent_progress(self, session_id: str, agent_type: str, result: dict) -> None:
        """發送解析進度通知"""
        try:
            # 準備進度詳細信息
            details = {}

            # 日期信息
            if "check_in" in result and "check_out" in result:
                details["日期"] = f"{result['check_in']} 到 {result['check_out']}"

            # 地點信息
            if result.get("county_ids"):
                details["地點"] = f"縣市ID: {result['county_ids']}"

            # 人數信息
            if result.get("adults"):
                guests = f"{result['adults']}成人"
                if result.get("children"):
                    guests += f", {result['children']}兒童"
                details["人數"] = guests

            # 預算信息
            if "lowest_price" in result and result["lowest_price"] > 0:
                details["預算"] = f"{result['lowest_price']} ~ {result.get('highest_price', result['lowest_price'])}"

            # 搜索結果信息
            for search_type, key in [
                ("搜索結果", "hotel_search_results"),
                ("模糊搜索結果", "fuzzy_search_results"),
                ("方案搜索結果", "plan_search_results"),
            ]:
                if key in result and isinstance(result[key], list):
                    details[search_type] = f"找到 {len(result[key])} 間旅館"

            # 構建消息
            message = f"{agent_type}已完成"
            if details:
                detail_str = "，".join([f"{k}: {v}" for k, v in details.items()])
                message += f"（{detail_str}）"

            # 發送進度通知到前端
            await ws_manager.broadcast_chat_message(
                session_id,
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

    def _process_search_results(self, key: str, result: dict, state: dict, function_name: str) -> None:
        """處理搜索結果並更新狀態"""
        # 檢查結果是否為有效列表
        if not isinstance(result[key], list):
            logger.warning(f"節點 {function_name} 返回的 {key} 不是列表類型")
            return

        # 結果為空列表
        if not result[key]:
            if key not in state:
                state[key] = []
            logger.warning(f"節點 {function_name} 返回了空的 {key}")
            return

        # 有效非空列表，更新狀態
        state[key] = result[key]
        results_count = len(state[key])
        logger.info(f"節點 {function_name} 返回了 {key}: {results_count} 個結果")

        # 記錄前三個結果的名稱
        if results_count > 0 and all(isinstance(item, dict) for item in state[key][:3]):
            sample_names = [item.get("name", "未知") for item in state[key][:3] if isinstance(item, dict)]
            logger.info(f"{key} 結果示例: {', '.join(sample_names)}")

    def _error_handler(self, state):
        """處理錯誤並中斷工作流"""
        error_msg = state.get("error", "未知錯誤")

        # 設置錯誤回應
        if "err_msg" not in state:
            logger.warning(f"工作流可預期異常: {error_msg}")
            state["text_response"] = state["err_msg"]
        else:
            logger.error(f"工作流執行異常: {error_msg}")
            state["text_response"] = f"很抱歉，處理您的查詢時發生錯誤: {error_msg}"

        # 確保有基本的回應結構
        if "response" not in state:
            state["response"] = {}

        state["response"]["status"] = "error"

        return state

    def _search_route_selector(self, state):
        """決定從搜索路由到哪些搜索節點"""
        # 檢查是否有錯誤
        if error := state.get("error"):
            logger.error(f"工作流執行錯誤: {error}")
            return ["response_generator"]

        # 獲取當前搜索重試次數，預設為0
        retry_count = state.get("search_retry_count", 0)
        MAX_SEARCH_RETRIES = 2

        # 檢查是否已達到最大重試次數
        if retry_count >= MAX_SEARCH_RETRIES:
            logger.warning(f"已達到最大重試次數 ({MAX_SEARCH_RETRIES})，不再嘗試搜索")
            state["message"] = f"未找到完全符合條件的旅館，已嘗試 {retry_count} 次。以下是最接近的結果。"
            return ["search_results_aggregator"]

        # 確定需要執行的搜索節點
        to_execute = []

        # 檢查關鍵字搜索條件
        if (
            state.get("keyword_parsed", False)
            and state.get("hotel_keyword")
            and not state.get("fuzzy_search_done", False)
        ):
            state["hotel_name"] = state.get("hotel_keyword", "")
            logger.info("添加旅館模糊搜索到執行清單")
            to_execute.append("hotel_search_fuzzy")

        # 檢查方案搜索條件
        if (
            state.get("keyword_parsed", False)
            and state.get("hotel_keyword")
            and state.get("date_parsed", False)
            and state.get("check_in")
            and state.get("check_out")
            and not state.get("plan_search_done", False)
        ):
            logger.info("添加旅館方案搜索到執行清單")
            to_execute.append("hotel_search_plan")

        # 檢查基本搜索條件
        county_id = self._get_county_id(state)
        if county_id and not state.get("hotel_search_done", False):
            # 設置基本搜索參數
            self._prepare_basic_search_params(state, county_id)
            logger.info("添加基本旅館搜索到執行清單")
            to_execute.append("hotel_search")

        # 檢查搜索狀態和結果
        all_searches_done = self._are_all_searches_done(state)
        has_any_results = self._has_any_search_results(state)

        # 處理搜索完成或沒有搜索條件的情況
        if all_searches_done or not to_execute:
            return self._handle_search_completion(state, has_any_results, retry_count, MAX_SEARCH_RETRIES)

        logger.info(f"將執行以下搜索節點: {to_execute}")
        return to_execute

    def _get_county_id(self, state):
        """從狀態中獲取縣市ID"""
        if state.get("geo_data") and state.get("geo_data", {}).get("county_id"):
            county_id = state.get("geo_data", {}).get("county_id", 0)
            logger.info(f"從 geo_data 獲取縣市ID: {county_id}")
            return county_id
        if state.get("destination", {}).get("county"):
            county_id = state.get("destination", {}).get("county")
            logger.info(f"從 destination 獲取縣市ID: {county_id}")
            return county_id
        if state.get("county_ids"):
            county_id = state.get("county_ids", [0])[0]
            logger.info(f"從 county_ids 獲取縣市ID: {county_id}")
            return county_id

        logger.warning("缺少縣市ID，無法執行基本旅館搜索")
        return 0

    def _are_all_searches_done(self, state):
        """檢查是否所有搜索都已完成"""
        return (
            (state.get("hotel_search_done", False) or not bool(state.get("county_ids")))
            and (state.get("fuzzy_search_done", False) or not state.get("hotel_keyword"))
            and (
                state.get("plan_search_done", False)
                or not (state.get("check_in") and state.get("check_out") and state.get("hotel_keyword"))
            )
        )

    def _has_any_search_results(self, state):
        """檢查是否有任何搜索結果"""
        return (
            bool(state.get("hotel_search_results"))
            or bool(state.get("fuzzy_search_results"))
            or bool(state.get("plan_search_results"))
        )

    def _prepare_basic_search_params(self, state, county_id):
        """準備基本搜索參數"""
        # 設置基本搜索參數
        state["hotel_search_params"] = {
            "county_id": county_id,
            "check_in": state.get("check_in", datetime.now().strftime("%Y-%m-%d")),
            "check_out": state.get("check_out", (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")),
            "adults": state.get("adults", 2),
            "children": state.get("children", 0),
            "lowest_price": state.get("lowest_price", 0),
            "highest_price": state.get("highest_price", 0),
        }
        logger.info(f"已準備基本搜索參數: {state['hotel_search_params']}")

    def _handle_search_completion(self, state, has_any_results, retry_count, max_retries):
        """處理搜索完成或沒有搜索條件的情況"""
        # 如果已有結果或達到最大重試次數，進入結果匯總階段
        if has_any_results or retry_count >= max_retries:
            if not has_any_results and retry_count >= max_retries:
                state["message"] = f"未找到符合條件的旅館，請嘗試調整搜索條件。(已嘗試 {retry_count} 次)"
            logger.info("所有搜索已完成或達到最大重試次數，進入結果匯總階段")
            return ["search_results_aggregator"]

        # 沒有結果且未達到最大重試次數，嘗試放寬條件重新搜索
        state["search_retry_count"] = retry_count + 1
        logger.warning(f"沒有搜索結果，嘗試放寬條件執行旅館搜索 (重試 {state['search_retry_count']}/{max_retries})")

        # 檢查是否有地理位置信息
        county_id = self._get_county_id(state)
        if county_id:
            # 重置搜索完成標記並執行基本搜索
            state["hotel_search_done"] = False
            logger.info("重試搜索，準備使用放寬條件")
            return ["hotel_search"]

        # 沒有地理資訊，直接進入結果匯總階段
        logger.info("沒有足夠的搜索條件，進入結果匯總階段")
        return ["search_results_aggregator"]

    def _search_to_router_condition(self, state):
        """決定是否需要將搜索節點連回搜索路由進行循環處理"""
        # 獲取重試次數和搜索結果狀態
        retry_count = state.get("search_retry_count", 0)
        max_retries = 2
        has_results = self._has_any_search_results(state)

        # 如果已有結果或達到最大重試次數，進入結果匯總階段
        if has_results or retry_count >= max_retries:
            logger.info("搜索已完成或達到最大重試次數，進入結果匯總階段")
            return ["search_results_aggregator"]

        # 檢查是否有其他搜索條件可以嘗試
        has_other_search_options = (not state.get("fuzzy_search_done") and state.get("hotel_keyword")) or (
            not state.get("plan_search_done")
            and state.get("check_in")
            and state.get("check_out")
            and state.get("hotel_keyword")
        )

        if has_other_search_options:
            logger.info(f"搜索未完成且有其他選項可用，重新進入搜索路由 (重試 {retry_count}/{max_retries})")
            return ["search_router"]

        # 默認進入結果匯總階段
        return ["search_results_aggregator"]

    async def run(self, query: str, session_id: str = "", user_query: str = "") -> dict:
        """
        運行工作流

        參數:
            query (str): 用戶查詢字符串（已轉換為繁體）
            session_id (str): 會話ID，用於WebSocket通信
            user_query (str): 原始用戶查詢（未轉換）

        返回:
            dict: 工作流運行結果
        """
        logger.info(f"開始處理查詢: {query}")

        # 初始狀態
        initial_state = {
            # 基本查詢信息
            "query": query,
            "query_original": query,
            "user_query": user_query,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            # 初始化空列表和字典
            "county_ids": [],
            "district_ids": [],
            "hotel_search_results": [],
            "fuzzy_search_results": [],
            "plan_search_results": [],
            "special_requirements": [],
            "supplies": [],
            # 初始化數值欄位
            "lowest_price": 0,
            "highest_price": 0,
            "adults": 0,
            "children": 0,
            # 初始化布爾欄位
            "has_breakfast": False,
            "has_lunch": False,
            "has_dinner": False,
            # 初始化字符串欄位
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
            "error": None,
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

    async def _send_poi_images(self, session_id: str, surroundings_map_images: list[dict]) -> None:
        """發送POI地圖圖片到前端"""
        try:
            if not surroundings_map_images:
                logger.warning("沒有POI地圖圖片可發送")
                return

            logger.info(f"開始發送 {len(surroundings_map_images)} 張POI地圖圖片到前端")

            # 構建圖片消息
            image_message = {
                "role": "system",
                "content_type": "poi_images",
                "content": "以下是旅館周邊地標地圖",
                "timestamp": asyncio.get_event_loop().time(),
                "images": surroundings_map_images,
            }

            # 發送圖片消息到前端
            await ws_manager.broadcast_chat_message(session_id, image_message)

            # 發送文字說明
            hotel_names = [img["hotel_name"] for img in surroundings_map_images]
            text_message = {
                "role": "system",
                "content": f"已為您提供以下旅館的周邊地標地圖：{', '.join(hotel_names)}",
                "timestamp": asyncio.get_event_loop().time(),
            }
            await ws_manager.broadcast_chat_message(session_id, text_message)

            logger.info("POI地圖圖片發送完成")
        except Exception as e:
            logger.error(f"發送POI地圖圖片失敗: {e}")


# 創建工作流實例（單例模式）
hotel_recommendation_workflow = HotelRecommendationWorkflow()


# 添加 run_workflow 函數，作為 hotel_recommendation_workflow.run 的包裝函數
async def run_workflow(data: dict | str, progress_callback=None) -> dict:
    """
    運行工作流的包裝函數

    參數:
        data (dict | str): 包含用戶查詢和上下文信息的字典或直接是查詢字符串
            - 如果是字典，應包含:
              - user_query (str): 用戶查詢
              - context (dict): 上下文信息
              - session_id (str): 會話ID
            - 如果是字符串，則直接作為用戶查詢
        progress_callback (callable): 進度回調函數，用於報告處理進度

    返回:
        dict: 工作流運行結果
    """
    # 處理不同類型的輸入
    if isinstance(data, str):
        user_query = data
        session_id = ""
        context = {}
    else:
        user_query = data.get("user_query", "")
        session_id = data.get("session_id", "")
        context = data.get("context", {})

    # 檢查查詢是否為空
    if not user_query:
        logger.error("用戶查詢為空")
        return {"error": "查詢內容為空", "text_response": "請提供查詢內容"}

    # 轉換為繁體中文
    query = hotel_recommendation_workflow.opencc.convert(user_query)
    logger.info(f"處理用戶查詢: {query}, 會話ID: {session_id}")

    # 如果有進度回調，報告開始解析查詢
    if progress_callback:
        await progress_callback("parse_query")

    # 設置超時時間（30秒）
    WORKFLOW_TIMEOUT = 30.0

    # 使用asyncio.wait_for添加超時機制
    try:
        # 使用超時機制運行工作流
        result = await asyncio.wait_for(
            hotel_recommendation_workflow.run(query=query, session_id=session_id, user_query=user_query),
            timeout=WORKFLOW_TIMEOUT,
        )

        # 如果有進度回調，報告處理完成
        if progress_callback:
            await progress_callback("final_response")

        return result
    except TimeoutError:
        logger.error(f"工作流執行超時 ({WORKFLOW_TIMEOUT}秒)")
        if progress_callback:
            await progress_callback("error", message=f"處理查詢超時 ({WORKFLOW_TIMEOUT}秒)")
        return {
            "error": f"處理查詢超時 ({WORKFLOW_TIMEOUT}秒)",
            "text_response": "很抱歉，處理您的查詢花費時間過長，請嘗試更簡單的查詢或稍後再試。",
        }
    except Exception as e:
        logger.error(f"工作流執行失敗: {e}")
        import traceback

        logger.error(f"詳細錯誤信息:\n{traceback.format_exc()}")
        if progress_callback:
            await progress_callback("error", message=str(e))
        return {
            "error": str(e),
            "text_response": f"很抱歉，處理您的查詢時發生錯誤: {e}",
        }
