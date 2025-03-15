"""
Multi-Agent 工作流程整合測試
"""

from datetime import datetime, timedelta

import pytest

from src.agents.generators.response_generator_agent import ResponseGeneratorAgent
from src.agents.parsers.budget_parser_agent import BudgetParserAgent
from src.agents.parsers.date_parser_agent import DateParserAgent
from src.agents.parsers.geo_parser_agent import GeoParserAgent
from src.agents.parsers.query_parser_agent import QueryParserAgent
from src.agents.search.hotel_search_agent import HotelSearchAgent
from src.agents.search.poi_search_agent import POISearchAgent

# Mock 資料
MOCK_HOTEL_DATA = [
    {
        "id": "hotel_001",
        "name": "台北大飯店",
        "address": "台北市中山區中山北路二段1號",
        "price": 3000,
        "rating": 4.5,
        "amenities": ["wifi", "parking", "restaurant"],
        "description": "位於市中心的五星級飯店",
        "latitude": 25.0522,
        "longitude": 121.5234,
    },
    {
        "id": "hotel_002",
        "name": "台北商務飯店",
        "address": "台北市信義區信義路五段5號",
        "price": 2500,
        "rating": 4.2,
        "amenities": ["wifi", "business_center", "gym"],
        "description": "商務人士首選的現代化飯店",
        "latitude": 25.0330,
        "longitude": 121.5654,
    },
]

MOCK_POI_DATA = [
    {
        "id": "poi_001",
        "name": "台北101",
        "type": "attraction",
        "address": "台北市信義區信義路五段7號",
        "latitude": 25.0330,
        "longitude": 121.5654,
        "rating": 4.8,
        "description": "台北地標建築",
        "distance": 0.5,  # 公里
    },
    {
        "id": "poi_002",
        "name": "信義商圈",
        "type": "shopping",
        "address": "台北市信義區信義路五段",
        "latitude": 25.0335,
        "longitude": 121.5660,
        "rating": 4.6,
        "description": "台北最繁華的商圈",
        "distance": 0.8,  # 公里
    },
]


@pytest.fixture
def mock_hotel_search():
    """模擬旅館搜索結果"""

    async def mock_search(*args, **kwargs):
        return MOCK_HOTEL_DATA

    return mock_search


@pytest.fixture
def mock_poi_search():
    """模擬景點搜索結果"""

    async def mock_search(*args, **kwargs):
        return MOCK_POI_DATA

    return mock_search


@pytest.fixture
def parsed_query_data():
    """模擬解析後的查詢資料"""
    return {
        "location": {"city": "台北市", "district": "信義區", "latitude": 25.0330, "longitude": 121.5654},
        "dates": {"check_in": datetime.now().date(), "check_out": (datetime.now() + timedelta(days=2)).date()},
        "guests": {"adults": 2, "children": 1},
        "budget": {"min": 2000, "max": 4000},
        "preferences": {"amenities": ["wifi", "parking"], "hotel_type": "business"},
    }


@pytest.mark.asyncio
async def test_multi_agent_workflow(mock_hotel_search, mock_poi_search, parsed_query_data):
    """測試完整的 Multi-Agent 工作流程"""
    # 1. 初始化各個 Agent
    query_parser = QueryParserAgent()
    date_parser = DateParserAgent()
    budget_parser = BudgetParserAgent()
    geo_parser = GeoParserAgent()
    hotel_search = HotelSearchAgent()
    poi_search = POISearchAgent()
    response_generator = ResponseGeneratorAgent()

    # 2. 模擬解析結果
    # 注意：在實際測試中，這些解析結果會來自真實的解析過程
    parsed_data = parsed_query_data

    # 3. 搜索旅館
    hotel_search._search = mock_hotel_search
    hotels = await hotel_search._process(parsed_data)
    assert len(hotels) > 0
    assert all(isinstance(hotel, dict) for hotel in hotels)
    assert all("id" in hotel for hotel in hotels)

    # 4. 搜索周邊景點
    poi_search._search = mock_poi_search
    pois = await poi_search._process({"location": parsed_data["location"], "hotels": hotels})
    assert len(pois) > 0
    assert all(isinstance(poi, dict) for poi in pois)
    assert all("id" in poi for poi in pois)

    # 5. 生成回應
    response = await response_generator._process({"query_data": parsed_data, "hotels": hotels, "pois": pois})

    # 6. 驗證回應
    assert isinstance(response, dict)
    assert "hotels" in response
    assert "pois" in response
    assert "summary" in response

    # 驗證旅館資訊
    assert len(response["hotels"]) == len(hotels)
    for hotel in response["hotels"]:
        assert "name" in hotel
        assert "price" in hotel
        assert "rating" in hotel
        assert "description" in hotel

    # 驗證景點資訊
    assert len(response["pois"]) == len(pois)
    for poi in response["pois"]:
        assert "name" in poi
        assert "type" in poi
        assert "distance" in poi
        assert "description" in poi

    # 驗證摘要
    assert isinstance(response["summary"], str)
    assert len(response["summary"]) > 0


@pytest.mark.asyncio
async def test_error_handling(mock_hotel_search, mock_poi_search, parsed_query_data):
    """測試錯誤處理"""
    # 1. 初始化 Agent
    hotel_search = HotelSearchAgent()
    poi_search = POISearchAgent()
    response_generator = ResponseGeneratorAgent()

    # 2. 模擬搜索失敗
    async def mock_failed_search(*args, **kwargs):
        raise Exception("搜索失敗")

    hotel_search._search = mock_failed_search

    # 3. 驗證錯誤處理
    with pytest.raises(Exception) as exc_info:
        await hotel_search._process(parsed_query_data)
    assert str(exc_info.value) == "搜索失敗"

    # 4. 模擬部分資料缺失
    incomplete_data = {
        "location": parsed_query_data["location"],
        "hotels": [],  # 空列表
    }

    # 5. 驗證部分資料缺失的處理
    pois = await poi_search._process(incomplete_data)
    assert len(pois) > 0  # 即使沒有旅館資料，仍然可以搜索景點

    # 6. 驗證回應生成器的錯誤處理
    response = await response_generator._process({"query_data": parsed_query_data, "hotels": [], "pois": pois})

    assert isinstance(response, dict)
    assert "hotels" in response
    assert "pois" in response
    assert "summary" in response
    assert len(response["hotels"]) == 0
    assert len(response["pois"]) > 0
