"""
地理資料快取模組，用於快取縣市和鄉鎮區資料
"""

import asyncio
from pathlib import Path
from typing import Any

import aiofiles
import faiss
import numpy as np
from loguru import logger
from orjson import dumps, loads
from sentence_transformers import SentenceTransformer

from src.api.services import hotel_api_service


class GeoCache:
    """地理資料快取類"""

    def __init__(self):
        """初始化地理資料快取"""
        self._counties: list[dict[str, Any]] = []
        self._counties_districts: list[dict[str, Any]] = []
        self._districts: list[dict[str, Any]] = []
        self._initialized = False
        self._lock = asyncio.Lock()

        # FAISS相關屬性
        self._model = None
        self._county_index = None
        self._district_index = None
        self._county_names = []
        self._district_names = []

        # 持久化相關屬性
        self._cache_dir = Path("./cache")
        self._counties_cache_path = self._cache_dir / "counties.json"
        self._districts_cache_path = self._cache_dir / "districts.json"
        self._county_names_cache_path = self._cache_dir / "county_names.json"
        self._district_names_cache_path = self._cache_dir / "district_names.json"
        self._county_index_cache_path = self._cache_dir / "county_index.bin"
        self._district_index_cache_path = self._cache_dir / "district_index.bin"
        self._counties_district_cache_path = self._cache_dir / "counties_district.json"

    async def initialize(self) -> None:
        """初始化快取資料"""
        async with self._lock:
            if self._initialized:
                logger.debug("地理資料快取已初始化，跳過")
                return

            logger.info("初始化地理資料快取")

            # 嘗試從磁碟加載快取
            if await self._load_cache_from_disk():
                self._initialized = True
                logger.info("從磁碟加載地理資料快取成功")
                return

            # 如果無法從磁碟加載，則從API獲取資料
            # 獲取縣市資料
            self._counties = await hotel_api_service.get_counties()
            logger.info(f"已快取 {len(self._counties)} 個縣市資料")

            # 獲取所有鄉鎮區資料
            self._districts = await hotel_api_service.get_districts()
            logger.info(f"已快取 {len(self._districts)} 個鄉鎮區資料")

            # 初始化FAISS索引
            await self._initialize_faiss()

            # 將資料保存到磁碟
            await self._save_cache_to_disk()

            # 從磁碟加載縣市對應鄉鎮資料
            async with aiofiles.open(self._counties_district_cache_path, "rb") as f:
                self._counties_districts = loads(await f.read())

            self._initialized = True
            logger.info("地理資料快取初始化完成")

    async def _load_cache_from_disk(self) -> bool:
        """從磁碟加載快取資料"""
        try:
            # 檢查所有快取文件是否存在
            if not all(
                [
                    self._counties_cache_path.exists(),
                    self._districts_cache_path.exists(),
                    self._county_names_cache_path.exists(),
                    self._district_names_cache_path.exists(),
                    self._county_index_cache_path.exists(),
                    self._district_index_cache_path.exists(),
                ]
            ):
                logger.info("快取文件不完整，需要重新初始化")
                return False

            # 加載基本資料
            tasks = [
                self._fetch_data_from_cache(self._counties_cache_path, "_counties"),
                self._fetch_data_from_cache(self._districts_cache_path, "_districts"),
                self._fetch_data_from_cache(self._county_names_cache_path, "_county_names"),
                self._fetch_data_from_cache(self._district_names_cache_path, "_district_names"),
            ]
            await asyncio.gather(*tasks)
            if not self._counties_district_cache_path.exists():
                logger.info("縣市對應鄉鎮資料不存在，需要重新初始化")
                from src.utils.geo_combine import combine_geo_data

                await combine_geo_data()
                return False
            # 從磁碟加載縣市對應鄉鎮資料
            async with aiofiles.open(self._counties_district_cache_path, "rb") as f:
                self._counties_districts = loads(await f.read())

            # 加載FAISS索引
            logger.info("從磁碟加載FAISS索引")
            self._county_index = faiss.read_index(str(self._county_index_cache_path))
            self._district_index = faiss.read_index(str(self._district_index_cache_path))

            # 加載模型 - 只在需要時加載一次
            if not self._model:
                logger.info("載入 Sentence Transformer 模型用於解析縣市地區")
                self._model = SentenceTransformer("distiluse-base-multilingual-cased-v2")

            logger.info(f"從磁碟加載了 {len(self._counties)} 個縣市和 {len(self._districts)} 個鄉鎮區資料")
        except Exception as e:
            logger.error(f"從磁碟加載快取失敗: {e}")
            return False
        return True

    async def _save_cache_to_disk(self) -> None:
        """將快取資料保存到磁碟"""
        try:
            # 確保快取目錄存在
            self._cache_dir.mkdir(parents=True, exist_ok=True)

            # 保存基本資料
            tasks = [
                self._store_data_in_cache(self._counties_cache_path, self._counties),
                self._store_data_in_cache(self._districts_cache_path, self._districts),
                self._store_data_in_cache(self._county_names_cache_path, self._county_names),
                self._store_data_in_cache(self._district_names_cache_path, self._district_names),
            ]
            await asyncio.gather(*tasks)

            # 保存FAISS索引
            if self._county_index and self._district_index:
                faiss.write_index(self._county_index, str(self._county_index_cache_path))
                faiss.write_index(self._district_index, str(self._district_index_cache_path))

            # 延遲載入轉換鄉鎮資料
            from src.utils.geo_combine import combine_geo_data

            await combine_geo_data()
            logger.info(f"已將地理資料快取保存到磁碟: {self._cache_dir}")
        except Exception as e:
            logger.error(f"保存快取到磁碟失敗: {e}")

    async def _initialize_faiss(self) -> None:
        """初始化FAISS索引"""
        try:
            # 載入模型 - 只在需要時加載一次
            if not self._model:
                logger.info("載入Sentence Transformer模型")
                self._model = SentenceTransformer("distiluse-base-multilingual-cased-v2")

            # 準備縣市名稱列表
            self._county_names = [county.get("name", "") for county in self._counties if county.get("name")]

            # 準備鄉鎮區名稱列表
            self._district_names = [district.get("name", "") for district in self._districts if district.get("name")]

            if not self._county_names or not self._district_names:
                logger.warning("縣市或鄉鎮區名稱列表為空，無法建立FAISS索引")
                return

            # 為縣市名稱建立FAISS索引 - 使用餘弦相似度而非L2距離
            logger.info("為縣市名稱建立FAISS索引")
            county_embeddings = self._model.encode(self._county_names)
            dimension = county_embeddings.shape[1]

            # 使用IndexFlatIP進行內積搜索（餘弦相似度），而非L2距離
            # 對於歸一化的向量，內積等同於餘弦相似度
            county_embeddings = self._normalize_embeddings(county_embeddings)
            self._county_index = faiss.IndexFlatIP(dimension)
            self._county_index.add(np.array(county_embeddings).astype("float32"))

            # 為鄉鎮區名稱建立FAISS索引
            logger.info("為鄉鎮區名稱建立FAISS索引")
            district_embeddings = self._model.encode(self._district_names)
            district_embeddings = self._normalize_embeddings(district_embeddings)

            self._district_index = faiss.IndexFlatIP(dimension)
            self._district_index.add(np.array(district_embeddings).astype("float32"))
            logger.info("FAISS索引建立完成")

            # 延遲載入轉換鄉鎮資料/初始化
            logger.info("初始化鄉鎮資料")
            from src.utils.geo_combine import combine_geo_data

            await combine_geo_data()
            logger.info("鄉鎮資料初始化完成")

        except Exception as e:
            logger.error(f"初始化FAISS索引失敗: {e}")
            # 如果FAISS初始化失敗，仍然可以使用傳統方法
            self._model = None
            self._county_index = None
            self._district_index = None

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """將嵌入向量歸一化，用於餘弦相似度計算"""
        faiss.normalize_L2(embeddings)
        return embeddings

    async def get_counties(self) -> list[dict[str, Any]]:
        """獲取縣市列表"""
        if not self._initialized:
            await self.initialize()
        return self._counties

    async def get_districts(self) -> list[dict[str, Any]]:
        """獲取鄉鎮區列表"""
        if not self._initialized:
            await self.initialize()
        return self._districts

    def get_county_by_name(self, name: str) -> dict[str, Any] | None:
        """根據名稱獲取縣市資料"""
        if not self._initialized:
            logger.warning("地理資料快取尚未初始化，無法查詢縣市資料")
            return None
        if len(name) < 2:
            logger.warning("縣市名稱過短，無法查詢縣市資料")
            return None

        # 標準化名稱處理（台/臺互換）
        normalized_name = name.replace("台", "臺") if "台" in name else name.replace("臺", "台")
        names_to_check = [name, normalized_name]

        # 嘗試使用FAISS進行相似度搜索
        if self._model and self._county_index and name:
            try:
                # 逐一檢查名稱以獲得最佳匹配
                best_overall_similarity = 0
                best_overall_index = -1

                for check_name in names_to_check:
                    # 對單個名稱進行嵌入計算，以獲得更準確的結果
                    query_embedding = self._model.encode([check_name])
                    query_embedding = self._normalize_embeddings(query_embedding)
                    # 使用餘弦相似度搜索，值越高表示越相似
                    similarities, indices = self._county_index.search(np.array(query_embedding).astype("float32"), 2)

                    # 檢查該名稱的最佳匹配
                    for i in range(len(similarities[0])):
                        if similarities[0][i] > best_overall_similarity and similarities[0][i] > 0.65:  # 閾值
                            best_overall_similarity = similarities[0][i]
                            best_overall_index = indices[0][i]

                # 如果找到結果且相似度足夠高
                if best_overall_index >= 0 and best_overall_index < len(self._county_names):
                    matched_name = self._county_names[best_overall_index]
                    logger.debug(f"FAISS匹配縣市: '{name}' -> '{matched_name}', 相似度: {best_overall_similarity}")

                    # 根據匹配的名稱找到對應的縣市資料
                    return next(county for county in self._counties if county.get("name") == matched_name)
            except Exception as e:
                logger.error(f"FAISS搜索縣市失敗: {e}")
                # 如果FAISS搜索失敗，回退到傳統方法

        # 傳統方法增強版：直接匹配（包括標準化名稱）
        for check_name in names_to_check:
            for county in self._counties:
                if county.get("name") == check_name:
                    return county

        # 傳統方法增強版：部分匹配（包括標準化名稱）
        for check_name in names_to_check:
            for county in self._counties:
                county_name = county.get("name", "")
                # 台/臺互換處理
                normalized_county = (
                    county_name.replace("台", "臺") if "台" in county_name else county_name.replace("臺", "台")
                )

                if (
                    check_name in county_name
                    or county_name in check_name
                    or check_name in normalized_county
                    or normalized_county in check_name
                ):
                    return county

        return None

    def get_district_by_name(self, name: str) -> dict[str, Any] | None:
        """根據名稱獲取鄉鎮區資料"""
        if not self._initialized:
            logger.warning("地理資料快取尚未初始化，無法查詢鄉鎮區資料")
            return None

        # 標準化名稱處理（台/臺互換）
        normalized_name = name.replace("台", "臺") if "台" in name else name.replace("臺", "台")
        names_to_check = [name, normalized_name]

        # 嘗試使用FAISS進行相似度搜索
        if self._model and self._district_index and name:
            try:
                # 逐一檢查名稱以獲得最佳匹配
                best_overall_similarity = 0
                best_overall_index = -1

                for check_name in names_to_check:
                    # 對單個名稱進行嵌入計算，以獲得更準確的結果
                    query_embedding = self._model.encode([check_name])
                    query_embedding = self._normalize_embeddings(query_embedding)
                    # 使用餘弦相似度搜索，值越高表示越相似
                    similarities, indices = self._district_index.search(np.array(query_embedding).astype("float32"), 2)

                    # 檢查該名稱的最佳匹配
                    for i in range(len(similarities[0])):
                        if similarities[0][i] > best_overall_similarity and similarities[0][i] > 0.65:  # 閾值
                            best_overall_similarity = similarities[0][i]
                            best_overall_index = indices[0][i]

                # 如果找到結果且相似度足夠高
                if best_overall_index >= 0 and best_overall_index < len(self._district_names):
                    matched_name = self._district_names[best_overall_index]
                    logger.debug(f"FAISS匹配鄉鎮區: '{name}' -> '{matched_name}', 相似度: {best_overall_similarity}")

                    # 根據匹配的名稱找到對應的鄉鎮區資料
                    for district in self._districts:
                        if district.get("name") == matched_name:
                            return district
            except Exception as e:
                logger.error(f"FAISS搜索鄉鎮區失敗: {e}")
                # 如果FAISS搜索失敗，回退到傳統方法

        # 傳統方法增強版：直接匹配（包括標準化名稱）
        for check_name in names_to_check:
            for district in self._districts:
                if district.get("name") == check_name:
                    return district

        # 傳統方法增強版：部分匹配（包括標準化名稱）
        for check_name in names_to_check:
            for district in self._districts:
                district_name = district.get("name", "")
                # 台/臺互換處理
                normalized_district = (
                    district_name.replace("台", "臺") if "台" in district_name else district_name.replace("臺", "台")
                )

                if any(check_name in part or part in check_name for part in district_name.split()) or any(
                    check_name in part or part in check_name for part in normalized_district.split()
                ):
                    return district

        return None

    def get_formatted_counties(self) -> dict[str, Any]:
        """獲取格式化的地理資料，用於LLM解析"""
        if not self._initialized:
            logger.warning("地理資料快取尚未初始化，無法獲取格式化地理資料")
            return {}

        formatted_data = {"counties": {}, "districts": {}}

        # 格式化縣市資料
        for county in self._counties:
            county_id = county.get("id")
            county_name = county.get("name")
            if county_id and county_name:
                formatted_data["counties"][county_name] = county_id

        # 格式化鄉鎮區資料
        for district in self._districts:
            district_id = district.get("id")
            district_name = district.get("name")
            if district_id and district_name:
                formatted_data["districts"][district_name] = district_id

        return formatted_data

    async def clear_cache(self) -> None:
        """清除快取資料（包括記憶體和磁碟）"""
        async with self._lock:
            # 清除記憶體中的資料
            self._counties = []
            self._districts = []
            self._county_names = []
            self._district_names = []
            self._county_index = None
            self._district_index = None
            self._initialized = False

            # 清除磁碟上的快取文件
            try:
                for cache_path in [
                    self._counties_cache_path,
                    self._districts_cache_path,
                    self._county_names_cache_path,
                    self._district_names_cache_path,
                    self._county_index_cache_path,
                    self._district_index_cache_path,
                ]:
                    if cache_path.exists():
                        cache_path.unlink()

                logger.info("已清除地理資料快取")
            except Exception as e:
                logger.error(f"清除磁碟快取失敗: {e}")

    async def _fetch_data_from_cache(self, path, attribute):
        async with aiofiles.open(path, "rb") as f:
            setattr(self, attribute, loads(await f.read()))

    async def _store_data_in_cache(self, path: Path, data: list[dict[str, Any]]):
        async with aiofiles.open(path, "wb") as f:
            await f.write(dumps(data))

    async def get_county_by_id(self, ids: list[int]) -> dict[str, Any] | None:
        """根據ID獲取縣市資料"""
        ids_list =[next(i for i in self._counties_districts if i.get("id")==id) for id in ids]
        return ids_list

    async def get_district_by_id(self, ids: list[int]) -> dict[str, Any] | None:
        """根據ID獲取鄉鎮區資料"""
        return next((district for district in self._counties_districts if district.get("id") == id), None)


# 創建地理資料快取實例
geo_cache = GeoCache()
