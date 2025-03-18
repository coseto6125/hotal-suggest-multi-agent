import asyncio
from collections import defaultdict

import aiofiles
import orjson


async def init_geo_data(counties_file: str, districts_file: str, counties_district_new_file: str) -> list:
    # 讀取文件
    async with aiofiles.open(counties_file, encoding="utf-8") as f:
        counties = orjson.loads(await f.read())
    async with aiofiles.open(districts_file, encoding="utf-8") as f:
        districts = orjson.loads(await f.read())
    async with aiofiles.open(counties_district_new_file, encoding="utf-8") as f:
        counties_district_new = orjson.loads(await f.read())

    # 創建縣市名稱到 ID 的映射，提前去除空白
    county_name_to_id = {county["name"].strip(): county["id"] for county in counties}

    # 創建地區名稱到地區列表的映射，處理可能的重複名稱
    district_name_to_districts = defaultdict(list)
    for district in districts:
        district_name_to_districts[district["name"].strip()].append(district)

    # 標準化 counties_district_new 的縣市和地區名稱
    counties_district_new_stripped = {
        county_name.strip(): [district_name.strip() for district_name in district_names]
        for county_name, district_names in counties_district_new.items()
    }

    # 初始化結果和縣市結構
    result = []
    county_structure = {}
    for county in counties:
        county_dict = {"id": county["id"], "name": county["name"], "districts": []}
        result.append(county_dict)
        county_structure[county["id"]] = county_dict
    used_districts = set()

    # 處理每個縣市及其地區
    for county_name, district_names in counties_district_new_stripped.items():
        if county_name in county_name_to_id:
            county_id = county_name_to_id[county_name]
            for district_name in district_names:
                if district_name in district_name_to_districts:
                    for district in district_name_to_districts[district_name]:
                        if district["id"] not in used_districts:
                            county_structure[county_id]["districts"].append(
                                {"id": district["id"], "name": district_name}
                            )
                            used_districts.add(district["id"])
                            break

    # 收集未使用的地區
    all_district_ids = set(district["id"] for district in districts)
    unused_district_ids = all_district_ids - used_districts
    if unused_district_ids:
        # 創建外國地區
        foreign_districts = []
        for id in unused_district_ids:
            for district in districts:
                if district["id"] == id:
                    foreign_districts.append({"id": id, "name": district["name"]})
                    break
        result.append({"id": None, "name": "foreign", "districts": foreign_districts})

    # 將空地區列表設置為 None
    for county in result:
        if county["districts"] == []:
            county["districts"] = None

    return result


async def combine_geo_data():
    counties_file = "cache/counties.json"
    districts_file = "cache/districts.json"
    counties_district_new_file = "cache/counties_district_new.json"
    result = await init_geo_data(counties_file, districts_file, counties_district_new_file)
    async with aiofiles.open("cache/counties_district.json", "wb") as f:
        await f.write(orjson.dumps(result, option=orjson.OPT_INDENT_2))


if __name__ == "__main__":
    import time

    start_time = time.time()
    asyncio.run(combine_geo_data())
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
