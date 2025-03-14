"""
測試 spaCy 地理名稱解析功能
"""

import asyncio
import time

import pytest
from loguru import logger

from src.cache.geo_cache import geo_cache
from src.utils.geo_parser import geo_parser


@pytest.mark.asyncio
async def test_geo_parser():
    """測試地理名稱解析器"""
    # 初始化地理資料快取和解析器
    await geo_cache.initialize()
    await geo_parser.initialize()

    # 測試查詢
    test_queries = [
        "我想在台北市找一家旅館",
        "幫我在台中市西屯區找一家飯店",
        "我需要在高雄市住宿",
        "我想在新北市淡水區找一家靠近海邊的民宿",
        "幫我找台南市的住宿",
        "我想在花蓮縣找一家有溫泉的旅館",
        "我需要在宜蘭縣礁溪鄉住宿",
        "我想在嘉義市找一家便宜的旅館",
        "幫我在屏東縣墾丁找一家海景飯店",
        "我想在苗栗縣找一家靠近火車站的旅館",
    ]

    logger.info(f"開始測試 spaCy 地理名稱解析功能，共 {len(test_queries)} 個測試查詢")

    total_time = 0
    success_count = 0

    for i, query in enumerate(test_queries, 1):
        logger.info(f"測試 {i}/{len(test_queries)}: {query}")

        start_time = time.time()
        geo_entities = await geo_parser.parse_geo_entities(query)
        end_time = time.time()

        parse_time = (end_time - start_time) * 1000
        total_time += parse_time

        logger.info(f"識別到的地理實體: {geo_entities}")
        logger.info(f"解析時間: {parse_time:.2f}ms")

        # 檢查是否至少識別出一個縣市或鄉鎮區
        has_geo_info = (
            len(geo_entities["counties"]) > 0
            or len(geo_entities["districts"]) > 0
            or geo_entities["destination"]["county"] is not None
            or geo_entities["destination"]["district"] is not None
        )

        if has_geo_info:
            logger.success("成功從查詢中識別出地理實體")
            success_count += 1
        else:
            logger.error("未能從查詢中識別出任何地理實體")

        logger.info("-" * 50)

    avg_time = total_time / len(test_queries)
    success_rate = (success_count / len(test_queries)) * 100

    logger.info(f"測試完成，平均解析時間: {avg_time:.2f}ms")
    logger.info(f"成功率: {success_rate:.2f}% ({success_count}/{len(test_queries)})")

    # 測試增強查詢功能
    logger.info("測試地理名稱解析器增強查詢功能")

    # 模擬一個沒有地理資訊的解析結果
    parsed_query = {
        "original_query": "我想在台北市信義區找一家靠近101的五星級飯店，預算5000以內",
        "dates": {"check_in": "2023-06-01", "check_out": "2023-06-03"},
        "guests": {"adults": 2, "children": 0},
        "budget": {"min": 0, "max": 5000},
        "hotel_type": "五星級飯店",
        "special_requirements": ["靠近101"],
    }

    # 使用地理名稱解析器增強查詢
    enhanced_query = await geo_parser.enhance_query_with_geo_data(parsed_query)

    logger.info(f"原始查詢: {parsed_query}")
    logger.info(f"增強後的查詢: {enhanced_query}")

    # 檢查是否正確識別出台北市和信義區
    if (
        "destination" in enhanced_query
        and enhanced_query["destination"].get("county")
        and enhanced_query["destination"].get("district")
    ):
        county_id = enhanced_query["destination"]["county"]
        district_id = enhanced_query["destination"]["district"]

        county = next((c for c in geo_cache._counties if c.get("id") == county_id), None)
        district = next((d for d in geo_cache._districts if d.get("id") == district_id), None)

        if county and district:
            county_name = county.get("name", "")
            district_name = district.get("name", "")

            logger.info(f"識別出的縣市: {county_name} ({county_id})")
            logger.info(f"識別出的鄉鎮區: {district_name} ({district_id})")

            if (county_name in {"臺北市", "台北市"}) and "信義" in district_name:
                logger.success("成功識別出正確的地理位置")
            else:
                logger.error(f"識別出的地理位置不正確，預期: 台北市信義區，實際: {county_name}{district_name}")
        else:
            logger.error("無法找到對應的縣市或鄉鎮區資料")
    else:
        logger.error("未能從查詢中識別出地理位置")


if __name__ == "__main__":
    asyncio.run(test_geo_parser())
