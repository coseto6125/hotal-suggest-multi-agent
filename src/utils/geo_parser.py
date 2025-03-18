"""
地理名稱解析模組，使用 spaCy 解析文本中的地名
"""

import asyncio
import re
from typing import Any

import spacy
from loguru import logger

from src.cache.geo_cache import geo_cache
from src.utils.nlp_utils import get_shared_spacy_model


class GeoParser:
    """地理名稱解析器"""

    def __init__(self):
        """初始化地理名稱解析器"""
        self._nlp = None
        self._initialized = False
        self._taiwan_counties = []
        self._taiwan_districts = []
        self._county_patterns = []
        self._district_patterns = []
        self._initialization_lock = asyncio.Lock()  # 直接在初始化時創建鎖
        self._model_loaded = False  # 標記模型是否已載入

    async def initialize(self) -> None:
        """初始化解析器"""
        if self._initialized:
            logger.debug("地理名稱解析器已初始化，跳過")
            return

        async with self._initialization_lock:
            # 再次檢查，以防在等待鎖的過程中已經被初始化
            if self._initialized:
                logger.debug("地理名稱解析器已在等待鎖的過程中被初始化，跳過")
                return

            logger.info("初始化地理名稱解析器")

            # 載入 spaCy 模型（如果尚未載入）
            await self._load_spacy_model()

            # 確保地理資料快取已初始化
            await geo_cache.initialize()

            # 獲取台灣縣市和鄉鎮區資料
            self._taiwan_counties = await geo_cache.get_counties()
            self._taiwan_districts = await geo_cache.get_districts()

            # 建立縣市和鄉鎮區的正則表達式模式
            self._build_geo_patterns()

            self._initialized = True
            logger.info("地理名稱解析器初始化完成")

    async def _load_spacy_model(self) -> None:
        """載入 spaCy 中文模型"""
        if self._model_loaded:
            logger.debug("spaCy 中文模型已載入，跳過")
            return

        # 載入 spaCy 模型
        try:
            logger.info("載入 spaCy 中文模型")
            self._nlp = get_shared_spacy_model("zh_core_web_md")
            logger.info("spaCy 中文模型載入成功")
            self._model_loaded = True
        except Exception as e:
            logger.error(f"載入 spaCy 模型失敗: {e}")
            # 如果無法載入模型，使用基本的 spaCy 功能
            self._nlp = spacy.blank("zh")
            logger.info("使用基本的 spaCy 功能")
            self._model_loaded = True

    def _build_geo_patterns(self) -> None:
        """建立地理名稱的正則表達式模式"""
        # 建立縣市名稱模式
        county_names = [county.get("name", "") for county in self._taiwan_counties if county.get("name")]
        # 移除空字串並排序，長的名稱優先匹配
        county_names = sorted([name for name in county_names if name], key=len, reverse=True)
        self._county_patterns = [re.compile(f"({re.escape(name)})", re.UNICODE) for name in county_names]

        # 建立鄉鎮區名稱模式
        district_names = [district.get("name", "") for district in self._taiwan_districts if district.get("name")]
        # 移除空字串並排序，長的名稱優先匹配
        district_names = sorted([name for name in district_names if name], key=len, reverse=True)
        self._district_patterns = [re.compile(f"({re.escape(name)})", re.UNICODE) for name in district_names]

        logger.info(f"已建立 {len(self._county_patterns)} 個縣市和 {len(self._district_patterns)} 個鄉鎮區的匹配模式")

    def _process_compound_location(self, text: str) -> list[tuple[str, str]]:
        """
        處理複合地名，例如"臺北南港"、"屏東恆春"等

        Args:
            text: 輸入文本

        Returns:
            列表，包含(縣市名稱, 鄉鎮區名稱)元組
        """
        compound_locations = []

        # 嘗試從文本中推斷複合地名
        for i in range(len(text)):
            # 考慮最長可能的地名（通常不超過8個字）
            for j in range(i + 3, min(i + 9, len(text) + 1)):
                potential_loc = text[i:j]

                # 檢查是否包含縣市名
                for county in self._taiwan_counties:
                    county_name = county.get("name", "")
                    if not county_name or len(county_name) < 2:
                        continue

                    # 處理台/臺互換
                    county_variations = [
                        county_name,
                        county_name.replace("台", "臺") if "台" in county_name else county_name.replace("臺", "台"),
                    ]

                    for county_var in county_variations:
                        if county_var in potential_loc:
                            # 移除縣市名稱，檢查剩餘部分是否為鄉鎮區
                            remaining = potential_loc.replace(county_var, "")
                            if remaining and len(remaining) >= 2:
                                # 嘗試匹配鄉鎮區
                                for district in self._taiwan_districts:
                                    district_name = district.get("name", "")
                                    if not district_name:
                                        continue

                                    # 處理台/臺互換
                                    district_variations = [
                                        district_name,
                                        district_name.replace("台", "臺")
                                        if "台" in district_name
                                        else district_name.replace("臺", "台"),
                                    ]

                                    for district_var in district_variations:
                                        # 檢查區名是否與剩餘部分匹配
                                        if (
                                            district_var == remaining
                                            or district_var in remaining
                                            or remaining in district_var
                                        ):
                                            logger.debug(
                                                f"推斷複合地名: {potential_loc} -> {county_name}, {district_name}"
                                            )
                                            compound_locations.append((county_name, district_name))
                                            break

                                    # 如果找到匹配，跳出內層循環
                                    if any(d[1] == district_name for d in compound_locations):
                                        break

                            # 如果找到匹配，跳出當前潛在地名的處理
                            if any(c[0] == county_name for c in compound_locations):
                                break

        return compound_locations

    async def preload_model(self) -> None:
        """預先載入 spaCy 模型，可在應用啟動時調用"""
        if not self._model_loaded:
            await self._load_spacy_model()

    async def parse_geo_entities(self, text: str) -> dict[str, Any]:
        """解析文本中的地理實體"""
        if not self._initialized:
            await self.initialize()

        result = {"counties": [], "districts": [], "destination": {"county": None, "district": None}}

        # 首先嘗試處理複合地名
        compound_locations = self._process_compound_location(text)

        # 如果找到複合地名，直接使用
        if compound_locations:
            county_name, district_name = compound_locations[0]

            # 獲取縣市ID
            county = geo_cache.get_county_by_name(county_name)
            if county and county.get("id"):
                county_id = county.get("id")
                result["counties"].append({"id": county_id, "name": county_name})
                result["destination"]["county"] = county_id
                logger.debug(f"從複合地名獲取縣市: {county_name} (ID: {county_id})")

            # 獲取鄉鎮區ID
            district = geo_cache.get_district_by_name(district_name)
            if district and district.get("id"):
                district_id = district.get("id")
                result["districts"].append({"id": district_id, "name": district_name})
                result["destination"]["district"] = district_id
                logger.debug(f"從複合地名獲取鄉鎮區: {district_name} (ID: {district_id})")

            # 如果已經成功處理複合地名，直接返回結果
            if result["destination"]["county"] and result["destination"]["district"]:
                logger.info(f"成功解析複合地名: {county_name}{district_name}")
                return result

        # 使用 spaCy 進行命名實體識別
        doc = self._nlp(text)

        # 從 spaCy 的實體中提取地點
        locations = []
        for ent in doc.ents:
            if ent.label_ in ["LOC", "GPE"]:
                locations.append(ent.text)
                logger.debug(f"spaCy 識別到地點: {ent.text} ({ent.label_})")

        # 使用正則表達式匹配縣市名稱
        counties = []
        for pattern in self._county_patterns:
            matches = pattern.findall(text)
            counties.extend(matches)

        # 使用正則表達式匹配鄉鎮區名稱
        districts = []
        for pattern in self._district_patterns:
            matches = pattern.findall(text)
            districts.extend(matches)

        # 增強識別：處理複合地名（例如"臺北南港"，"屏東恆春"等）
        # 用於存儲已識別的複合地名
        compound_locations = []

        # 嘗試將文本中可能的地名組合分離出來
        for i in range(len(text)):
            # 考慮最長可能的地名（例如最多4個字）
            for j in range(i + 2, min(i + 6, len(text) + 1)):
                potential_loc = text[i:j]

                # 檢查是否包含縣市名
                for county_name in sorted(
                    [c.get("name", "") for c in self._taiwan_counties if c.get("name")], key=len, reverse=True
                ):
                    if county_name in potential_loc and len(county_name) >= 2:
                        # 移除縣市名稱，檢查剩餘部分是否為鄉鎮區
                        remaining = potential_loc.replace(county_name, "")
                        if remaining:
                            for district_name in sorted(
                                [d.get("name", "") for d in self._taiwan_districts if d.get("name")],
                                key=len,
                                reverse=True,
                            ):
                                if district_name == remaining or district_name in remaining:
                                    logger.debug(
                                        f"識別到複合地名: {potential_loc} (縣市: {county_name}, 鄉鎮區: {district_name})"
                                    )
                                    counties.append(county_name)
                                    districts.append(district_name)
                                    compound_locations.append((county_name, district_name))
                                    break

        # 合併 spaCy 識別的地點和正則表達式匹配的結果
        for loc in locations:
            # 檢查是否為縣市
            county = geo_cache.get_county_by_name(loc)
            if county:
                counties.append(loc)
                continue

            # 檢查是否為鄉鎮區
            district = geo_cache.get_district_by_name(loc)
            if district:
                districts.append(loc)

        # 去重
        counties = list(set(counties))
        districts = list(set(districts))

        # 將縣市名稱轉換為 ID
        county_ids = []
        for county_name in counties:
            county = geo_cache.get_county_by_name(county_name)
            if county:
                county_id = county.get("id")
                if county_id:
                    county_ids.append({"id": county_id, "name": county_name})
                    logger.debug(f"縣市 '{county_name}' 轉換為 ID: {county_id}")

        # 將鄉鎮區名稱轉換為 ID
        district_ids = []
        for district_name in districts:
            district = geo_cache.get_district_by_name(district_name)
            if district:
                district_id = district.get("id")
                if district_id:
                    district_ids.append({"id": district_id, "name": district_name})
                    logger.debug(f"鄉鎮區 '{district_name}' 轉換為 ID: {district_id}")

        # 更新結果
        result["counties"] = county_ids
        result["districts"] = district_ids

        # 設置目的地 - 優先使用複合地名
        if compound_locations:
            # 使用第一個識別到的複合地名
            county_name, district_name = compound_locations[0]

            # 設置縣市
            county = geo_cache.get_county_by_name(county_name)
            if county and county.get("id"):
                result["destination"]["county"] = county.get("id")

            # 設置鄉鎮區
            district = geo_cache.get_district_by_name(district_name)
            if district and district.get("id"):
                result["destination"]["district"] = district.get("id")
        else:
            # 如果沒有複合地名，使用原來的邏輯
            if county_ids:
                result["destination"]["county"] = county_ids[0]["id"]
            if district_ids:
                result["destination"]["district"] = district_ids[0]["id"]

        return result

    async def enhance_query_with_geo_data(self, parsed_query: dict[str, Any]) -> dict[str, Any]:
        """使用地理資料增強解析結果"""
        if not parsed_query:
            return parsed_query

        # 如果已經有目的地資訊，不需要增強
        if parsed_query.get("destination", {}).get("county") or parsed_query.get("destination", {}).get("district"):
            logger.debug("解析結果已包含目的地資訊，跳過增強")
            return parsed_query

        # 從原始查詢中提取地理實體
        original_query = parsed_query.get("original_query", "")
        if not original_query:
            logger.debug("解析結果中沒有原始查詢，跳過增強")
            return parsed_query

        # 檢查是否已經有解析過的地理實體
        if "geo_entities" in parsed_query:
            logger.debug("使用已解析的地理實體進行增強")
            geo_entities = parsed_query["geo_entities"]
        else:
            logger.debug("重新解析地理實體進行增強")
            geo_entities = await self.parse_geo_entities(original_query)

        # 如果沒有找到地理實體，返回原始解析結果
        if not geo_entities["counties"] and not geo_entities["districts"]:
            logger.debug("未找到地理實體，返回原始解析結果")
            return parsed_query

        # 更新目的地資訊
        if "destination" not in parsed_query:
            parsed_query["destination"] = {}

        if geo_entities["destination"]["county"]:
            parsed_query["destination"]["county"] = geo_entities["destination"]["county"]
            logger.debug(f"增強解析結果：添加縣市 ID {geo_entities['destination']['county']}")

        if geo_entities["destination"]["district"]:
            parsed_query["destination"]["district"] = geo_entities["destination"]["district"]
            logger.debug(f"增強解析結果：添加鄉鎮區 ID {geo_entities['destination']['district']}")

        return parsed_query


# 創建地理名稱解析器實例
geo_parser = GeoParser()
