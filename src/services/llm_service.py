"""
LLM 服務，用於與語言模型進行交互
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from loguru import logger
from orjson import loads
from src.config import config


class LLMService:
    """LLM 服務"""

    def __init__(self):
        """初始化LLM服務"""
        self.provider = config.llm.provider

        if self.provider == "openai":
            self.llm = ChatOpenAI(
                api_key=config.llm.openai_api_key, model="gpt-4-turbo", temperature=0.7, streaming=True
            )
        elif self.provider == "ollama" and config.ollama.enabled:
            self.llm = ChatOllama(
                model=config.ollama.model, base_url=config.ollama.base_url, temperature=config.ollama.temperature
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")

        logger.info(f"初始化LLM服務，提供商: {self.provider}")

    async def generate_response(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        """生成回應"""
        # TODO: 實現生成回應的邏輯
        langchain_messages = []

        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))

        for message in messages:
            if message["role"] == "user":
                langchain_messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                langchain_messages.append(AIMessage(content=message["content"]))

        response = await self.llm.ainvoke(langchain_messages)
        return response.content

    async def stream_response(self, messages: list[dict[str, str]], system_prompt: str | None = None):
        """流式生成回應"""
        # TODO: 實現流式生成回應的邏輯
        langchain_messages = []

        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))

        for message in messages:
            if message["role"] == "user":
                langchain_messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                langchain_messages.append(AIMessage(content=message["content"]))

        async for chunk in self.llm.astream(langchain_messages):
            yield chunk.content

    async def parse_user_query(self, query: str) -> dict[str, Any]:
        """解析用戶查詢，提取關鍵參數"""
        # TODO: 實現解析用戶查詢的邏輯
        system_prompt = """
        你是一個旅館推薦系統的查詢解析器。
        你的任務是從用戶的自然語言查詢中提取關鍵參數，以便系統可以使用這些參數來搜索旅館。
        請從用戶查詢中提取以下參數（如果存在）：
        - 目的地（縣市和鄉鎮區）
        - 旅遊日期（入住日期和退房日期）
        - 人數（成人和兒童）
        - 預算（每晚價格範圍）
        - 旅館類型（如飯店、民宿等）
        - 特殊需求（如設施、服務等）
        
        請以JSON格式返回結果，格式如下：
        {
            "destination": {
                "county": "縣市名稱",
                "district": "鄉鎮區名稱"
            },
            "dates": {
                "check_in": "YYYY-MM-DD",
                "check_out": "YYYY-MM-DD"
            },
            "guests": {
                "adults": 成人數量,
                "children": 兒童數量
            },
            "budget": {
                "min": 最低價格,
                "max": 最高價格
            },
            "hotel_type": "旅館類型",
            "special_requirements": ["需求1", "需求2", ...]
        }
        
        如果某些參數未在查詢中提及，請將其設置為null。
        """

        messages = [{"role": "user", "content": query}]
        response = await self.generate_response(messages, system_prompt)
        import re

        # 使用正則表達式提取JSON字符串
        json_pattern = re.compile(r'```json\n(.*?)\n```', re.DOTALL)
        match = json_pattern.search(response)
        
        try:
            json_str = match.group(1)
            return loads(json_str)
        except Exception as e:
            logger.error(f"解析用戶查詢失敗: {e!s}")
            return {}


# 創建LLM服務實例
llm_service = LLMService()
