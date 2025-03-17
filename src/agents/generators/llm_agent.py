"""
LLM Agent，用於與語言模型進行交互
"""

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from loguru import logger
from orjson import loads

from src.agents.base.base_agent import BaseAgent
from src.cache.geo_cache import geo_cache
from src.config import config
from src.utils.geo_parser import geo_parser


class LLMAgent(BaseAgent):
    """LLM Agent - 負責與語言模型進行交互"""

    def __init__(self):
        """初始化LLM Agent"""
        super().__init__("LLMAgent")
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

        logger.info(f"初始化LLM Agent，提供商: {self.provider}")

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理LLM相關請求的方法"""
        # 檢查請求類型並相應處理
        request_type = state.get("llm_request_type", "")

        if request_type == "generate_response":
            messages = state.get("messages", [])
            system_prompt = state.get("system_prompt")
            response = await self.generate_response(messages, system_prompt)
            return {**state, "response": response}

        if request_type == "parse_user_query":
            query = state.get("query", "")
            geo_entities = state.get("geo_entities")
            parsed_query = await self.parse_user_query(query, geo_entities)
            return {**state, "parsed_query": parsed_query}

        # 其他請求類型可以在這裡添加...

        # 如果沒有特定的請求類型或不需要處理，返回原始狀態
        return state

    async def generate_response(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        """生成回應"""
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

    async def parse_user_query(self, query: str, geo_entities: dict[str, Any] = None) -> dict[str, Any]:
        """
        解析用戶查詢，提取關鍵參數

        Args:
            query: 用戶查詢
            geo_entities: 已解析的地理實體，如果提供則不會重複解析
        """
        # 初始化地理資料快取
        await geo_cache.initialize()

        # 如果沒有提供已解析的地理實體，則進行解析
        if geo_entities is None:
            geo_entities = await geo_parser.parse_geo_entities(query)
            logger.debug("在 LLMAgent.parse_user_query 中解析地理實體")

        # 獲取 spaCy 識別的縣市和鄉鎮區名稱
        counties_str = ", ".join([county.get("name", "") for county in geo_entities.get("counties", [])])
        districts_str = ", ".join([district.get("name", "") for district in geo_entities.get("districts", [])])

        # JSON 格式範例 - 不作為 f-string 的一部分
        json_format = """
{
    "destination": {
        "county": "縣市ID",
        "district": "鄉鎮區ID"
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
"""

        # 構建系統提示，包含地理資料和 spaCy 解析結果
        system_prompt = f"""
        你是一個旅館推薦系統的查詢解析器。
        你的任務是從用戶的自然語言查詢中提取關鍵參數，以便系統可以使用這些參數來搜索旅館。
        請從用戶查詢中提取以下參數（如果存在）：
        - 目的地（縣市和鄉鎮區）
        - 旅遊日期（入住日期和退房日期）
        - 人數（成人和兒童）
        - 預算（每晚價格範圍）
        - 旅館類型（如飯店、民宿等）
        - 特殊需求（如設施、服務等）
        
        我們已經使用 spaCy 從用戶查詢中識別出以下地理實體：
        縣市: {counties_str}
        鄉鎮區: {districts_str}
        
        請以JSON格式返回結果，格式如下：
{json_format}
        
        如果某些參數未在查詢中提及，請將其設置為null。
        
        對於目的地，請優先使用我們通過 spaCy 識別的地理實體。如果 spaCy 已經識別出縣市或鄉鎮區，請直接使用這些資訊。
        """

        messages = [{"role": "user", "content": query}]
        response = await self.generate_response(messages, system_prompt)

        # 使用正則表達式提取JSON字符串
        json_pattern = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
        match = json_pattern.search(response)

        try:
            if match:
                json_str = match.group(1)
                parsed_query = loads(json_str)
            else:
                # 嘗試直接解析整個回應
                parsed_query = loads(response)

            # 如果 LLM 沒有提供地理資訊，但 spaCy 有識別出地理實體，則使用 spaCy 的結果
            if not parsed_query.get("destination", {}).get("county") and geo_entities["destination"]["county"]:
                if "destination" not in parsed_query:
                    parsed_query["destination"] = {}
                parsed_query["destination"]["county"] = geo_entities["destination"]["county"]

            if not parsed_query.get("destination", {}).get("district") and geo_entities["destination"]["district"]:
                if "destination" not in parsed_query:
                    parsed_query["destination"] = {}
                parsed_query["destination"]["district"] = geo_entities["destination"]["district"]

            # 驗證解析結果中的地理資料
            self._validate_geo_data(parsed_query)

            return parsed_query
        except Exception as e:
            logger.error(f"解析用戶查詢失敗: {e!s}")
            # 如果解析失敗，至少返回 spaCy 識別的地理實體
            return {"destination": geo_entities["destination"]}

    def _validate_geo_data(self, parsed_query: dict[str, Any]) -> None:
        """驗證並修正解析結果中的地理資料"""
        if not parsed_query or "destination" not in parsed_query:
            return

        destination = parsed_query.get("destination", {})
        if not destination:
            return

        # 獲取縣市和鄉鎮區
        county_name = destination.get("county")
        district_name = destination.get("district")

        # 如果縣市是字符串而不是ID，嘗試查找對應的ID
        if county_name and isinstance(county_name, str) and not county_name.startswith(("TPE", "NWT", "TAO", "TXG")):
            county = geo_cache.get_county_by_name(county_name)
            if county:
                destination["county"] = county.get("id")
            else:
                destination["county"] = None

        # 如果鄉鎮區是字符串而不是ID，嘗試查找對應的ID
        if (
            district_name
            and isinstance(district_name, str)
            and not district_name.startswith(("TPE-", "NWT-", "TAO-", "TXG-"))
        ):
            district = geo_cache.get_district_by_name(district_name)
            if district:
                destination["district"] = district.get("id")
            else:
                destination["district"] = None

        # 更新解析結果
        parsed_query["destination"] = destination


# 創建LLM Agent實例
llm_agent = LLMAgent()
