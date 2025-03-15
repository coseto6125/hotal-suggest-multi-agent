import asyncio
from datetime import datetime

import pytest
from loguru import logger

from src.models.hotel import Hotel, Room, RoomType
from src.services.hotel_service import HotelService
from src.services.llm_service import LLMService


@pytest.fixture
def mock_hotel_data():
    """模擬飯店資料"""
    return Hotel(
        id="H001",
        name="台北大飯店",
        address="台北市中山區中山北路二段1號",
        description="位於市中心的五星級飯店",
        rating=4.8,
        price_range={"min": 3000, "max": 15000},
        amenities=["wifi", "parking", "gym", "pool"],
        images=["https://example.com/hotel1.jpg"],
        rooms=[
            Room(
                id="R001",
                type=RoomType.STANDARD,
                price=5000,
                capacity=2,
                description="標準雙人房",
                amenities=["wifi", "tv", "ac"],
                images=["https://example.com/room1.jpg"],
            ),
            Room(
                id="R002",
                type=RoomType.DELUXE,
                price=8000,
                capacity=4,
                description="豪華四人房",
                amenities=["wifi", "tv", "ac", "jacuzzi"],
                images=["https://example.com/room2.jpg"],
            ),
        ],
    )


@pytest.fixture
def mock_parsed_query():
    """模擬解析後的查詢結果"""
    return {
        "original_query": "我想在台北找一家有游泳池的五星級飯店，預算5000-8000元，兩大一小，8月15日入住兩晚",
        "search_mode": "filter",
        "hotel_group_types": ["飯店"],
        "check_in": "2024-08-15",
        "check_out": "2024-08-17",
        "adults": 2,
        "children": 1,
        "lowest_price": 5000,
        "highest_price": 8000,
        "county_ids": ["TPE"],
        "district_ids": ["ZSN"],
        "hotel_facility_ids": ["POOL"],
        "room_facility_ids": [],
        "has_breakfast": True,
        "has_lunch": False,
        "has_dinner": False,
        "special_requirements": ["五星級", "游泳池"],
    }


@pytest.mark.asyncio
async def test_hotel_recommendation_flow(mock_parsed_query):
    """測試飯店推薦系統完整流程"""
    try:
        # 1. 初始化服務
        hotel_service = HotelService()
        llm_service = LLMService()

        # 2. 搜尋符合條件的飯店
        logger.info("開始搜尋符合條件的飯店...")
        hotels = await hotel_service.search_hotels(
            location=mock_parsed_query["county_ids"][0],
            check_in=datetime.strptime(mock_parsed_query["check_in"], "%Y-%m-%d"),
            check_out=datetime.strptime(mock_parsed_query["check_out"], "%Y-%m-%d"),
            adults=mock_parsed_query["adults"],
            children=mock_parsed_query["children"],
            min_price=mock_parsed_query["lowest_price"],
            max_price=mock_parsed_query["highest_price"],
            has_breakfast=mock_parsed_query["has_breakfast"],
            has_lunch=mock_parsed_query["has_lunch"],
            has_dinner=mock_parsed_query["has_dinner"],
            hotel_facility_ids=mock_parsed_query["hotel_facility_ids"],
            room_facility_ids=mock_parsed_query["room_facility_ids"],
            special_requirements=mock_parsed_query["special_requirements"],
        )

        assert len(hotels) > 0, "應該找到至少一間符合條件的飯店"
        logger.info(f"找到 {len(hotels)} 間符合條件的飯店")

        # 3. 使用 LLM 分析飯店資訊並生成推薦
        logger.info("開始生成飯店推薦...")
        recommendation = await llm_service.generate_hotel_recommendation(hotels=hotels, parsed_query=mock_parsed_query)

        assert recommendation is not None, "應該成功生成推薦"
        logger.info(f"推薦內容: {recommendation}")

        # 4. 使用 LLM 生成回覆訊息
        logger.info("開始生成回覆訊息...")
        response = await llm_service.generate_response(
            original_query=mock_parsed_query["original_query"],
            parsed_query=mock_parsed_query,
            hotels=hotels,
            recommendation=recommendation,
        )

        assert response is not None, "應該成功生成回覆訊息"
        logger.info(f"回覆訊息: {response}")

        logger.success("飯店推薦系統流程測試通過！")

    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e!s}")
        raise


@pytest.mark.asyncio
async def test_recommendation_with_different_queries():
    """測試不同查詢情境的推薦結果"""
    test_cases = [
        {
            "parsed_query": {
                "original_query": "我想在台北找間飯店，預算大概5000到8000之間，兩個大人，要含早餐",
                "search_mode": "filter",
                "hotel_group_types": ["飯店"],
                "check_in": "2024-08-15",
                "check_out": "2024-08-16",
                "adults": 2,
                "children": 0,
                "lowest_price": 5000,
                "highest_price": 8000,
                "county_ids": ["TPE"],
                "district_ids": [],
                "hotel_facility_ids": [],
                "room_facility_ids": [],
                "has_breakfast": True,
                "has_lunch": False,
                "has_dinner": False,
                "special_requirements": [],
            }
        },
        {
            "parsed_query": {
                "original_query": "幫我找墾丁的住宿，要四人房含早餐",
                "search_mode": "filter",
                "hotel_group_types": ["飯店", "民宿"],
                "check_in": "2024-08-15",
                "check_out": "2024-08-16",
                "adults": 4,
                "children": 0,
                "lowest_price": 0,
                "highest_price": 0,
                "county_ids": ["PIF"],
                "district_ids": [],
                "hotel_facility_ids": [],
                "room_facility_ids": [],
                "has_breakfast": True,
                "has_lunch": False,
                "has_dinner": False,
                "special_requirements": [],
            }
        },
        {
            "parsed_query": {
                "original_query": "想訂宜蘭礁溪的溫泉飯店，兩大兩小，最多一晚12000，要包含晚餐跟早餐",
                "search_mode": "filter",
                "hotel_group_types": ["飯店"],
                "check_in": "2024-08-15",
                "check_out": "2024-08-16",
                "adults": 2,
                "children": 2,
                "lowest_price": 0,
                "highest_price": 12000,
                "county_ids": ["ILA"],
                "district_ids": ["JIAO"],
                "hotel_facility_ids": ["SPA"],
                "room_facility_ids": [],
                "has_breakfast": True,
                "has_lunch": False,
                "has_dinner": True,
                "special_requirements": ["溫泉"],
            }
        },
    ]

    hotel_service = HotelService()
    llm_service = LLMService()

    for case in test_cases:
        try:
            parsed_query = case["parsed_query"]
            logger.info(f"\n測試查詢: {parsed_query['original_query']}")

            # 1. 搜尋飯店
            hotels = await hotel_service.search_hotels(
                location=parsed_query["county_ids"][0],
                check_in=datetime.strptime(parsed_query["check_in"], "%Y-%m-%d"),
                check_out=datetime.strptime(parsed_query["check_out"], "%Y-%m-%d"),
                adults=parsed_query["adults"],
                children=parsed_query["children"],
                min_price=parsed_query["lowest_price"],
                max_price=parsed_query["highest_price"],
                has_breakfast=parsed_query["has_breakfast"],
                has_lunch=parsed_query["has_lunch"],
                has_dinner=parsed_query["has_dinner"],
                hotel_facility_ids=parsed_query["hotel_facility_ids"],
                room_facility_ids=parsed_query["room_facility_ids"],
                special_requirements=parsed_query["special_requirements"],
            )

            # 2. 生成推薦
            recommendation = await llm_service.generate_hotel_recommendation(hotels=hotels, parsed_query=parsed_query)

            # 3. 生成回覆
            response = await llm_service.generate_response(
                original_query=parsed_query["original_query"],
                parsed_query=parsed_query,
                hotels=hotels,
                recommendation=recommendation,
            )

            logger.success(f"查詢 '{parsed_query['original_query']}' 推薦測試通過")

        except Exception as e:
            logger.error(f"查詢 '{parsed_query['original_query']}' 推薦測試失敗: {e!s}")
            raise


if __name__ == "__main__":
    asyncio.run(test_recommendation_with_different_queries())
