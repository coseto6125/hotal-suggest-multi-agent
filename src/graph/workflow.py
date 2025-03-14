"""
LangGraph 工作流，定義代理之間的協作流程
"""

from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from loguru import logger

from src.agents.hotel_search_agent import hotel_search_agent
from src.agents.poi_search_agent import poi_search_agent
from src.agents.query_parser_agent import query_parser_agent
from src.agents.response_generator_agent import response_generator_agent


# 定義工作流狀態類型
class WorkflowState(TypedDict):
    """工作流狀態"""

    user_query: str
    parsed_query: dict[str, Any]
    original_query: str
    hotels: list[dict[str, Any]]
    hotel_details: list[dict[str, Any]]
    search_params: dict[str, Any]
    poi_results: list[dict[str, Any]]
    response: str
    initial_response: str
    error: str


# 定義節點函數
async def parse_query(state: WorkflowState) -> WorkflowState:
    """解析查詢節點"""
    # TODO: 實現解析查詢節點
    logger.info("執行解析查詢節點")

    user_query = state.get("user_query", "")
    result = await query_parser_agent.run({"user_query": user_query})

    # 更新狀態
    new_state = state.copy()
    new_state["parsed_query"] = result.get("parsed_query", {})
    new_state["original_query"] = result.get("original_query", "")

    # 檢查錯誤
    if "error" in result:
        new_state["error"] = result["error"]

    return new_state


async def search_hotels(state: WorkflowState) -> WorkflowState:
    """搜索旅館節點"""
    # TODO: 實現搜索旅館節點
    logger.info("執行搜索旅館節點")

    parsed_query = state.get("parsed_query", {})
    result = await hotel_search_agent.run({"parsed_query": parsed_query})

    # 更新狀態
    new_state = state.copy()
    new_state["hotels"] = result.get("hotels", [])
    new_state["hotel_details"] = result.get("hotel_details", [])
    new_state["search_params"] = result.get("search_params", {})

    # 檢查錯誤
    if "error" in result:
        new_state["error"] = result["error"]

    return new_state


async def search_pois(state: WorkflowState) -> WorkflowState:
    """搜索周邊地標節點"""
    # TODO: 實現搜索周邊地標節點
    logger.info("執行搜索周邊地標節點")

    hotels = state.get("hotels", [])
    result = await poi_search_agent.run({"hotels": hotels})

    # 更新狀態
    new_state = state.copy()
    new_state["poi_results"] = result.get("poi_results", [])

    # 檢查錯誤
    if "error" in result:
        new_state["error"] = result["error"]

    return new_state


async def generate_initial_response(state: WorkflowState) -> WorkflowState:
    """生成初步回應節點"""
    # TODO: 實現生成初步回應節點
    logger.info("執行生成初步回應節點")

    original_query = state.get("original_query", "")
    hotels = state.get("hotels", [])

    # 生成簡單的初步回應
    initial_response = "我正在為您搜索符合條件的旅館和周邊景點，請稍候..."

    if hotels:
        hotel_names = [hotel.get("name", "未知") for hotel in hotels[:3]]
        hotel_names_str = "、".join(hotel_names)
        initial_response = (
            f"我找到了一些符合您要求的旅館，包括{hotel_names_str}等。正在為您整理詳細信息和周邊景點，請稍候..."
        )

    # 更新狀態
    new_state = state.copy()
    new_state["initial_response"] = initial_response

    return new_state


async def generate_final_response(state: WorkflowState) -> WorkflowState:
    """生成最終回應節點"""
    # TODO: 實現生成最終回應節點
    logger.info("執行生成最終回應節點")

    original_query = state.get("original_query", "")
    hotels = state.get("hotels", [])
    hotel_details = state.get("hotel_details", [])
    poi_results = state.get("poi_results", [])

    result = await response_generator_agent.run(
        {"original_query": original_query, "hotels": hotels, "hotel_details": hotel_details, "poi_results": poi_results}
    )

    # 更新狀態
    new_state = state.copy()
    new_state["response"] = result.get("response", "")

    # 檢查錯誤
    if "error" in result:
        new_state["error"] = result["error"]

    return new_state


def should_end_on_error(state: WorkflowState) -> str:
    """檢查是否因錯誤結束"""
    if state.get("error"):
        return "end"
    return "continue"


# 創建工作流圖
def create_workflow() -> StateGraph:
    """創建工作流圖"""
    # TODO: 實現創建工作流圖
    workflow = StateGraph(WorkflowState)

    # 添加節點
    workflow.add_node("parse_query", parse_query)
    workflow.add_node("search_hotels", search_hotels)
    workflow.add_node("search_pois", search_pois)
    workflow.add_node("generate_initial_response", generate_initial_response)
    workflow.add_node("generate_final_response", generate_final_response)

    # 設置邊
    workflow.set_entry_point("parse_query")
    workflow.add_edge("parse_query", "search_hotels")
    workflow.add_conditional_edges(
        "search_hotels", should_end_on_error, {"continue": "generate_initial_response", "end": END}
    )
    workflow.add_edge("generate_initial_response", "search_pois")
    workflow.add_conditional_edges(
        "search_pois", should_end_on_error, {"continue": "generate_final_response", "end": END}
    )
    workflow.add_edge("generate_final_response", END)

    return workflow


# 創建工作流實例
workflow_graph = create_workflow()
workflow = workflow_graph.compile()

# 創建內存保存器
memory_saver = MemorySaver()


async def run_workflow(user_query: str) -> dict[str, Any]:
    """運行工作流"""
    # TODO: 實現運行工作流
    logger.info(f"運行工作流，用戶查詢: {user_query}")

    # 初始化狀態
    initial_state = WorkflowState(
        user_query=user_query,
        parsed_query={},
        original_query="",
        hotels=[],
        hotel_details=[],
        search_params={},
        poi_results=[],
        response="",
        initial_response="",
        error="",
    )

    # 運行工作流
    result = await workflow.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": user_query}},
    )

    return result
