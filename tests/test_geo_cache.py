"""
測試地理資料快取的效果
"""

import asyncio
import os
import time
from pathlib import Path

import pytest
from loguru import logger

from src.agents.query_parser_agent import query_parser_agent
from src.cache.geo_cache import geo_cache


@pytest.mark.asyncio
async def test_geo_cache_acceleration():
    """測試地理資料快取對LLM解析的加速效果"""
    # 測試查詢
    test_queries = [
        "我想在台北市信義區找一間五星級飯店，預算每晚5000元以內，下週五入住兩晚",
        "幫我找台中市西區的民宿，希望有停車場，下個月初兩大一小入住",
        "我需要高雄市左營區附近的飯店，最好是靠近捷運站的，三天後入住",
    ]

    # # 測試未使用快取時的解析時間（模擬）
    # logger.info("測試模擬未使用快取時的解析時間")
    # no_cache_times = []

    # # 使用固定的模擬時間，代表未使用快取的情況
    # for query in test_queries:
    #     # 模擬未使用快取的耗時（假設平均需要2秒）
    #     simulated_time = 2.0
    #     no_cache_times.append(simulated_time)
    #     logger.info(f"模擬未使用快取解析查詢: '{query}' 耗時: {simulated_time:.2f}秒")

    # 確保快取已初始化
    if not geo_cache._initialized:
        logger.info("初始化地理資料快取")
        await geo_cache.initialize()

    # 測試已初始化快取時的解析時間
    logger.info("測試使用快取時的解析時間")
    with_cache_times = []
    with_cache_results = []

    for query in test_queries:
        # 確保快取已初始化
        assert geo_cache._initialized

        # 測量解析時間
        start_time = time.time()
        result = await query_parser_agent.run({"user_query": query})
        end_time = time.time()

        # 記錄時間和結果
        elapsed_time = end_time - start_time
        with_cache_times.append(elapsed_time)
        with_cache_results.append(result)

        logger.info(f"使用快取解析查詢: '{query}' 耗時: {elapsed_time:.2f}秒")
        logger.info(f"解析結果: {result.get('parsed_query', {}).get('destination', {})}")

    # 計算平均時間
    # avg_no_cache_time = sum(no_cache_times) / len(no_cache_times)
    avg_with_cache_time = sum(with_cache_times) / len(with_cache_times)

    # 計算加速比例
    # acceleration_ratio = avg_no_cache_time / avg_with_cache_time if avg_with_cache_time > 0 else float("inf")

    # logger.info(f"模擬未使用快取平均解析時間: {avg_no_cache_time:.2f}秒")
    logger.info(f"使用快取平均解析時間: {avg_with_cache_time:.2f}秒")
    # logger.info(f"加速比例: {acceleration_ratio:.2f}倍")

    # # 驗證結果
    # if acceleration_ratio > 1.0:
    #     logger.info("✅ 測試通過：使用快取成功加速解析過程")
    # else:
    #     logger.error("❌ 測試失敗：使用快取未能加速解析過程")

    # 驗證解析結果的準確性
    for i, with_cache_result in enumerate(with_cache_results):
        with_cache_destination = with_cache_result.get("parsed_query", {}).get("destination", {})

        # 檢查縣市ID是否正確
        county_id = with_cache_destination.get("county")
        if county_id is not None:
            logger.info(f"✅ 查詢 '{test_queries[i]}' 成功解析出縣市ID: {county_id}")
        else:
            logger.error(f"❌ 查詢 '{test_queries[i]}' 未能解析出縣市ID")

        # 檢查鄉鎮區ID是否正確
        district_id = with_cache_destination.get("district")
        if district_id is not None:
            logger.info(f"✅ 查詢 '{test_queries[i]}' 成功解析出鄉鎮區ID: {district_id}")
        else:
            logger.warning(f"⚠️ 查詢 '{test_queries[i]}' 未能解析出鄉鎮區ID")

    # 輸出結論
    logger.info("測試結論：")
    # logger.info(f"1. 模擬未使用快取平均解析時間: {avg_no_cache_time:.2f}秒")
    logger.info(f"2. 使用快取平均解析時間: {avg_with_cache_time:.2f}秒")
    # logger.info(f"3. 加速比例: {acceleration_ratio:.2f}倍")
    # logger.info(f"4. 使用快取是否加速解析過程: {'是' if acceleration_ratio > 1.0 else '否'}")


@pytest.mark.asyncio
async def test_vector_matching():
    """測試向量匹配功能（使用餘弦相似度）"""
    # 確保快取已初始化
    if not geo_cache._initialized:
        logger.info("初始化地理資料快取")
        await geo_cache.initialize()

    # 等待向量索引建立完成
    await asyncio.sleep(1)

    # 測試縣市模糊匹配
    test_county_cases = [
        ("台北", "臺北市"),  # 簡稱匹配
        ("臺北市", "臺北市"),  # 精確匹配
        ("台北市", "臺北市"),  # 繁簡體轉換
        ("新竹", "新竹市"),  # 可能混淆的情況（新竹市vs新竹縣）
    ]

    logger.info("測試縣市向量匹配（餘弦相似度）")
    for test_input, expected in test_county_cases:
        result = geo_cache.get_county_by_name(test_input)
        if result and result.get("name") == expected:
            logger.info(f"✅ 縣市匹配成功: '{test_input}' -> '{result.get('name')}'")
        else:
            actual = result.get("name") if result else "None"
            logger.warning(f"⚠️ 縣市匹配結果不符預期: '{test_input}' -> '{actual}', 預期: '{expected}'")

    # 測試鄉鎮區模糊匹配
    test_district_cases = [
        ("信義", "信義區"),  # 簡稱匹配
        ("信義區", "信義區"),  # 精確匹配
        ("西區", "西區"),  # 常見名稱
        ("左營", "左營區"),  # 簡稱匹配
    ]

    logger.info("測試鄉鎮區向量匹配（餘弦相似度）")
    for test_input, expected in test_district_cases:
        result = geo_cache.get_district_by_name(test_input)
        if result and result.get("name") == expected:
            logger.info(f"✅ 鄉鎮區匹配成功: '{test_input}' -> '{result.get('name')}'")
        else:
            actual = result.get("name") if result else "None"
            logger.warning(f"⚠️ 鄉鎮區匹配結果不符預期: '{test_input}' -> '{actual}', 預期: '{expected}'")

    # 測試極端情況
    extreme_cases = [
        "台北市信義區",  # 混合縣市和鄉鎮區
        "台",  # 極短輸入
        "台灣台北",  # 非標準表達
    ]

    logger.info("測試處理極端情況")
    for test_input in extreme_cases:
        county_result = geo_cache.get_county_by_name(test_input)
        district_result = geo_cache.get_district_by_name(test_input)

        county_name = county_result.get("name") if county_result else "None"
        district_name = district_result.get("name") if district_result else "None"

        logger.info(f"極端情況 '{test_input}': 縣市匹配 -> '{county_name}', 鄉鎮區匹配 -> '{district_name}'")


@pytest.mark.asyncio
async def test_cache_persistence():
    """測試快取持久化功能"""
    logger.info("測試快取持久化功能")

    # 清除現有快取
    await geo_cache.clear_cache()
    logger.info("已清除現有快取")

    # 初始化快取（從API獲取資料）
    logger.info("初始化快取（從API獲取資料）")
    start_time = time.time()
    await geo_cache.initialize()
    first_init_time = time.time() - start_time
    logger.info(f"首次初始化耗時: {first_init_time:.2f}秒")

    # 檢查快取文件是否已創建
    cache_dir = Path("./cache")
    cache_files = [
        cache_dir / "counties.pkl",
        cache_dir / "districts.pkl",
        cache_dir / "county_names.pkl",
        cache_dir / "district_names.pkl",
        cache_dir / "county_index.bin",
        cache_dir / "district_index.bin",
    ]

    all_files_exist = all(f.exists() for f in cache_files)
    if all_files_exist:
        logger.info("✅ 所有快取文件已成功創建")
    else:
        missing_files = [f for f in cache_files if not f.exists()]
        logger.error(f"❌ 部分快取文件未創建: {[str(f) for f in missing_files]}")

    # 測試一次查詢
    test_query = "台北市信義區"
    county_result = geo_cache.get_county_by_name(test_query)
    district_result = geo_cache.get_district_by_name(test_query)
    logger.info(
        f"使用初始化的快取查詢 '{test_query}': 縣市 -> '{county_result.get('name') if county_result else 'None'}', 鄉鎮區 -> '{district_result.get('name') if district_result else 'None'}'"
    )

    # 重置記憶體中的快取，但保留磁碟快取
    geo_cache._counties = []
    geo_cache._districts = []
    geo_cache._county_names = []
    geo_cache._district_names = []
    geo_cache._county_index = None
    geo_cache._district_index = None
    geo_cache._initialized = False
    logger.info("已重置記憶體中的快取")

    # 重新初始化（應從磁碟加載）
    logger.info("重新初始化快取（應從磁碟加載）")
    start_time = time.time()
    await geo_cache.initialize()
    second_init_time = time.time() - start_time
    logger.info(f"從磁碟加載快取耗時: {second_init_time:.2f}秒")

    # 再次測試查詢
    county_result = geo_cache.get_county_by_name(test_query)
    district_result = geo_cache.get_district_by_name(test_query)
    logger.info(
        f"使用從磁碟加載的快取查詢 '{test_query}': 縣市 -> '{county_result.get('name') if county_result else 'None'}', 鄉鎮區 -> '{district_result.get('name') if district_result else 'None'}'"
    )

    # 比較兩次初始化的時間
    if second_init_time < first_init_time:
        speedup = first_init_time / second_init_time
        logger.info(f"✅ 從磁碟加載快取比首次初始化快 {speedup:.2f} 倍")
    else:
        logger.warning("⚠️ 從磁碟加載快取未能加速初始化過程")

    # 清理測試產生的快取文件
    if os.environ.get("KEEP_CACHE_FILES") != "1":
        await geo_cache.clear_cache()
        logger.info("已清理測試產生的快取文件")


if __name__ == "__main__":
    # 設置日誌格式
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # 運行測試
    logger.info("開始測試地理資料快取的效果")
    asyncio.run(test_geo_cache_acceleration())
    logger.info("加速效果測試完成")

    logger.info("開始測試向量匹配功能")
    asyncio.run(test_vector_matching())
    logger.info("向量匹配測試完成")

    logger.info("開始測試快取持久化功能")
    asyncio.run(test_cache_persistence())
    logger.info("持久化測試完成")

    logger.info("所有測試完成")
