"""
測試解析器實例化的簡單腳本
"""

try:
    print("正在嘗試導入解析器實例...")
    from src.agents.parsers.instances import (
        budget_parser_agent,
        date_parser_agent,
        food_req_parser_agent,
        geo_parser_agent,
        guest_parser_agent,
        hotel_type_parser_agent,
        keyword_parser_agent,
        special_req_parser_agent,
        supply_parser_agent,
    )

    print("成功導入所有解析器實例")
    print(f"budget_parser_agent 類型: {type(budget_parser_agent)}")
    print(f"date_parser_agent 類型: {type(date_parser_agent)}")
    print(f"food_req_parser_agent 類型: {type(food_req_parser_agent)}")
    print(f"geo_parser_agent 類型: {type(geo_parser_agent)}")
    print(f"guest_parser_agent 類型: {type(guest_parser_agent)}")
    print(f"hotel_type_parser_agent 類型: {type(hotel_type_parser_agent)}")
    print(f"keyword_parser_agent 類型: {type(keyword_parser_agent)}")
    print(f"special_req_parser_agent 類型: {type(special_req_parser_agent)}")
    print(f"supply_parser_agent 類型: {type(supply_parser_agent)}")

    print("所有解析器實例化成功!")
except Exception as e:
    print(f"發生錯誤: {e}")
