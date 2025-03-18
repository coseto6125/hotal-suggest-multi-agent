#!/usr/bin/env python
import asyncio
import sys

from loguru import logger

from src.graph.workflow import HotelRecommendationWorkflow


async def main():
    """
    測試旅館推薦系統工作流
    """
    # 設置日誌級別
    logger.remove()
    logger.add(sys.stderr, level="TRACE")

    # 創建工作流實例
    workflow = HotelRecommendationWorkflow()

    # 測試查詢
    query = "我想在台北大同區找一間旅館，兩個大人一個小孩，預算5000以下，3月18日到3月21日"

    # 運行工作流
    logger.info(f"開始處理查詢: {query}")
    result = await workflow.run(query)

    # 輸出結果
    logger.info("處理結果:")
    logger.info(result.get("text_response", "無回應"))


if __name__ == "__main__":
    asyncio.run(main())
