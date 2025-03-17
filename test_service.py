"""
測試服務，看看是否解決了循環導入問題
"""

import asyncio
import time
import traceback

import orjson
from loguru import logger

from src.agents.generators.hotel_recommendation_agent import hotel_recommendation_agent
from src.cache.geo_cache import geo_cache
from src.graph.workflow import run_workflow


async def test_workflow():
    """測試工作流程能否成功運行"""
    try:
        # 先確保地理資料快取已初始化
        print("正在初始化地理資料快取...")
        await geo_cache.initialize()
        print("地理資料快取初始化完成")

        # 設置詳細的日誌記錄
        logger.info("啟用詳細調試模式")
        # 記錄開始時間
        start_time = time.time()

        # 定義測試查詢
        test_query = "我想在台北住一個晚上，預算3000元"
        print(f"使用測試查詢: '{test_query}'")

        print("正在嘗試運行工作流程...")
        result = await run_workflow(
            {
                "conversation_id": "test_conversation",
                "user_query": test_query,
            }
        )

        # 記錄完成時間
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"工作流程運行成功! 執行時間: {execution_time:.2f} 秒")
        print(f"結果類型: {type(result)}")

        # 檢查關鍵數據是否存在
        if isinstance(result, dict):
            print("\n===== 檢查關鍵數據 =====")
            # 檢查是否有旅館搜索結果
            if "hotel_search_results" in result:
                hotel_count = len(result.get("hotel_search_results", []))
                print(f"旅館搜索結果: {hotel_count} 間旅館")

                # 檢查第一個旅館的設施資料類型
                if hotel_count > 0:
                    first_hotel = result["hotel_search_results"][0]
                    if "facilities" in first_hotel:
                        facilities = first_hotel["facilities"]
                        print(f"設施數量: {len(facilities)}")
                        if facilities and len(facilities) > 0:
                            first_facility = facilities[0]
                            print(f"第一個設施類型: {type(first_facility)}")
                            if isinstance(first_facility, dict) and "name" in first_facility:
                                print(f"設施名稱類型: {type(first_facility['name'])}, 值: {first_facility['name']}")
            else:
                print("警告: 未找到旅館搜索結果")

            # 檢查清洗後的旅館數據
            if "clean_hotels" in result:
                clean_hotel_count = len(result.get("clean_hotels", []))
                print(f"清洗後旅館數據: {clean_hotel_count} 間旅館")

                # 顯示第一個旅館的關鍵資訊
                if clean_hotel_count > 0:
                    first_hotel = result["clean_hotels"][0]
                    print("\n第一間旅館資訊摘要:")
                    print(f"  名稱: {first_hotel.get('name', '未知')}")
                    print(f"  價格: {first_hotel.get('price', '未知')}")
                    print(f"  評分: {first_hotel.get('rating_text', '未知')}")

                    # 檢查房型資訊
                    if "room_types" in first_hotel:
                        print(f"  房型數量: {len(first_hotel['room_types'])}")

                    # 檢查設施資訊
                    if "facilities" in first_hotel and "popular" in first_hotel["facilities"]:
                        print(f"  熱門設施: {', '.join(first_hotel['facilities']['popular'][:3])}")
            else:
                print("警告: 未找到清洗後的旅館數據")

            # 檢查LLM準備資料
            if "llm_ready_data" in result:
                print("\nLLM準備資料檢查:")
                llm_data = result["llm_ready_data"]
                print(f"  含有旅館資料: {'是' if llm_data.get('hotels') else '否'}")
                print(f"  含有方案資料: {'是' if llm_data.get('plans') else '否'}")
                print(f"  保存查詢: {llm_data.get('query', '無')}")

                # 顯示LLM資料的前100個字符作為示例
                hotels_preview = (
                    (llm_data.get("hotels", "")[:100] + "...")
                    if len(llm_data.get("hotels", "")) > 100
                    else llm_data.get("hotels", "")
                )
                print(f"\nLLM旅館資料預覽:\n{hotels_preview}")
            else:
                print("警告: 未找到LLM準備資料")

            # 檢查LLM生成的推薦
            if "recommendation_response" in result:
                rec_text = result["recommendation_response"]
                text_length = len(rec_text)
                print(f"\nLLM推薦回應長度: {text_length} 字符")
                # 顯示回應的前150個字符作為示例
                preview = (rec_text[:150] + "...") if text_length > 150 else rec_text
                print(f"推薦回應預覽:\n{preview}")
            else:
                print("警告: 未找到LLM推薦回應")

                # 如果沒有LLM回應，嘗試直接調用HotelRecommendationAgent
                if "llm_ready_data" in result:
                    print("\n嘗試直接調用HotelRecommendationAgent...")
                    llm_result = await test_llm_directly(result)
                    if llm_result:
                        print("直接調用HotelRecommendationAgent成功!")
                        # 將生成的回應添加到結果中
                        result["recommendation_response"] = llm_result
                    else:
                        print("直接調用HotelRecommendationAgent失敗!")

        # 顯示完整結果或LLM生成結果
        print("\n===== LLM生成結果 =====")
        if isinstance(result, dict) and "recommendation_response" in result:
            print(result["recommendation_response"])
        elif isinstance(result, dict):
            print(orjson.dumps(result, option=orjson.OPT_INDENT_2).decode("utf-8"))
        else:
            print(result)
        print("======================\n")

        return True
    except Exception as e:
        print(f"工作流程運行失敗: {e}")
        traceback.print_exc()
        return False


async def test_llm_directly(state=None):
    """直接測試HotelRecommendationAgent的LLM回應生成"""
    try:
        print("\n===== 直接測試LLM回應生成 =====")

        # 檢查LLM服務狀態
        print("檢查LLM服務狀態...")
        try:
            # 簡單測試LLM服務是否可用
            test_message = [{"role": "user", "content": "測試訊息"}]
            test_response = await llm_service.get_response(test_message, "你是一個測試助手")
            print(f"LLM服務測試回應: {test_response[:30]}...")
            print("LLM服務正常運作")
        except Exception as e:
            print(f"LLM服務測試失敗: {e}")
            traceback.print_exc()
            return False

        # 如果沒有提供狀態，創建測試數據
        if not state:
            state = {
                "conversation_id": "test_direct",
                "query": "我想在台北住一個晚上，預算3000元",
                "llm_ready_data": {
                    "hotels": """【旅館1】台北君悅酒店
地址: 台北市信義區松壽路2號
位置: 台北市信義區
價格: NT$ 4,500
評價: 非常好
入住: 上午11:00, 退房: 下午12:00
主要設施: 免費無線網路, 停車場, 游泳池
客房類型:
  - 豪華雙人房: NT$ 4,500, 可住2人
  - 行政套房: NT$ 6,800, 可住3人
簡介: 台北君悅酒店位於台北市信義區，鄰近台北101和信義商圈，提供豪華住宿體驗。
取消政策: 入住前3天免費取消""",
                    "plans": "",
                    "query": "我想在台北住一個晚上，預算3000元",
                },
            }

        # 直接調用HotelRecommendationAgent
        print("正在調用HotelRecommendationAgent...")
        start_time = time.time()
        result = await hotel_recommendation_agent.process(state)
        end_time = time.time()

        # 檢查結果
        if "recommendation_response" in result:
            rec_text = result["recommendation_response"]
            print(f"生成成功! 用時: {end_time - start_time:.2f}秒")
            print(f"回應長度: {len(rec_text)} 字符")

            # 顯示回應
            print("\n===== 直接生成的LLM回應 =====")
            print(rec_text)
            print("==============================\n")
            return rec_text
        print("警告: 直接調用未能生成LLM回應")
        return False

    except Exception as e:
        print(f"直接測試LLM回應生成失敗: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        print("正在測試服務...")
        success = asyncio.run(test_workflow())
        if success:
            print("測試成功!")
        else:
            print("測試失敗!")
    except Exception as e:
        print(f"發生錯誤: {e}")
        traceback.print_exc()
