"""
協調器Agent，負責協調多個子Agent的執行流程
"""

import asyncio
from typing import Any, dict

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.agents.budget_parser_agent import budget_parser_agent
from src.agents.date_parser_agent import date_parser_agent
from src.agents.food_req_parser_agent import food_req_parser_agent
from src.agents.geo_parser_agent import geo_parser_agent
from src.agents.guest_parser_agent import guest_parser_agent
from src.agents.hotel_search_fuzzy_agent import hotel_search_fuzzy_agent
from src.agents.hotel_search_plan_agent import hotel_search_plan_agent
from src.agents.hotel_type_parser_agent import hotel_type_parser_agent
from src.agents.keyword_parser_agent import keyword_parser_agent
from src.agents.response_generator_agent import response_generator_agent
from src.agents.special_req_parser_agent import special_req_parser_agent


class OrchestratorAgent(BaseAgent):
    """協調器Agent，負責協調多個子Agent的執行流程"""

    def __init__(self):
        """初始化協調器Agent"""
        super().__init__("OrchestratorAgent")

    async def _process(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """處理用戶請求，協調多個子Agent的執行流程"""
        query = inputs.get("user_query", "")
        context = inputs.get("context", {})

        logger.info(f"開始處理用戶請求: {query}")

        # 保存原始查詢，以便後續使用
        context["original_query"] = query

        # 第一階段：併發執行解析子Agent
        parsed_data = await self._run_parsing_agents(query, context)

        # 將解析結果添加到上下文中
        context["parsed_data"] = parsed_data

        # 第二階段：併發執行搜索子Agent
        search_results = await self._run_search_agents(query, context)

        # 將搜索結果添加到上下文中
        context["search_results"] = search_results

        # 第三階段：生成回應
        response = await self._generate_response(query, context)

        return response

    async def _run_parsing_agents(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """併發執行解析子Agent"""
        logger.info("開始併發執行解析子Agent")

        # 創建所有解析子Agent的任務
        tasks = [
            budget_parser_agent.process_query(query, context),
            date_parser_agent.process_query(query, context),
            geo_parser_agent.process_query(query, context),
            guest_parser_agent.process_query(query, context),
            keyword_parser_agent.process_query(query, context),
            special_req_parser_agent.process_query(query, context),
            food_req_parser_agent.process_query(query, context),
            hotel_type_parser_agent.process_query(query, context),
        ]

        # 併發執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理結果
        parsed_data = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"解析子Agent執行失敗: {result!s}")
                continue

            # 合併結果
            parsed_data.update(result)

        logger.info(f"解析子Agent執行完成，解析結果: {parsed_data}")
        return parsed_data

    async def _run_search_agents(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """併發執行搜索子Agent"""
        logger.info("開始併發執行搜索子Agent")

        # 創建搜索子Agent的任務
        tasks = []

        # 如果有關鍵字，執行模糊搜索
        if "keywords" in context.get("parsed_data", {}):
            tasks.append(hotel_search_fuzzy_agent.process_query(query, context))

        # 如果有足夠的搜索條件，執行計劃搜索
        if self._has_sufficient_search_params(context.get("parsed_data", {})):
            tasks.append(hotel_search_plan_agent.process_query(query, context))

        # 如果沒有任務，返回空結果
        if not tasks:
            logger.warning("沒有足夠的搜索條件，無法執行搜索")
            return {}

        # 併發執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理結果
        search_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"搜索子Agent執行失敗: {result!s}")
                continue

            # 合併結果
            search_results.update(result)

        logger.info(f"搜索子Agent執行完成，搜索結果數量: {len(search_results)}")
        return search_results

    def _has_sufficient_search_params(self, parsed_data: dict[str, Any]) -> bool:
        """檢查是否有足夠的搜索條件"""
        # 至少需要日期和地點信息
        has_dates = (
            "dates" in parsed_data and parsed_data["dates"].get("check_in") and parsed_data["dates"].get("check_out")
        )
        has_geo = "geo" in parsed_data and (
            parsed_data["geo"].get("county_ids") or parsed_data["geo"].get("district_ids")
        )

        return has_dates and has_geo

    async def _generate_response(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """生成回應"""
        logger.info("開始生成回應")

        # 調用回應生成子Agent
        response = await response_generator_agent.process_query(query, context)

        logger.info("回應生成完成")
        return response


# 創建協調器Agent實例
orchestrator_agent = OrchestratorAgent()
