"""
查詢解析Agent，負責解析用戶查詢
"""

from typing import Any

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.services.llm_service import llm_service


class QueryParserAgent(BaseAgent):
    """查詢解析Agent"""

    def __init__(self):
        """初始化查詢解析Agent"""
        super().__init__("QueryParserAgent")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理用戶查詢"""
        # TODO: 實現查詢解析邏輯
        user_query = inputs.get("user_query", "")

        if not user_query:
            return {"error": "用戶查詢為空"}

        logger.info(f"解析用戶查詢: {user_query}")

        # 使用LLM解析用戶查詢
        parsed_query = await llm_service.parse_user_query(user_query)

        return {"parsed_query": parsed_query, "original_query": user_query}


# 創建查詢解析Agent實例
query_parser_agent = QueryParserAgent()
