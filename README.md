# 旅館查詢解析系統

本系統實現了一個模組化的旅館查詢解析系統，能夠從用戶的自然語言查詢中提取各種參數，用於搜索旅館。

## 系統架構

系統採用模組化設計，將查詢解析任務拆分為多個專門的子Agent，每個子Agent負責解析查詢中的特定部分。主查詢解析Agent協調各個子Agent的工作，並整合它們的解析結果。

### 子Agent列表

1. **地理名稱解析子Agent (GeoParserAgent)**
   - 負責解析查詢中的地理名稱，如縣市和鄉鎮區
   - 使用spaCy和正則表達式進行解析
   - 支持模糊匹配和相似度搜索

2. **日期解析子Agent (DateParserAgent)**
   - 負責解析查詢中的旅遊日期，如入住日期和退房日期
   - 支持多種日期格式，包括YYYY-MM-DD、MM-DD和中文日期格式
   - 能夠處理相對日期，如"今天"、"明天"、"這週末"等

3. **人數解析子Agent (GuestParserAgent)**
   - 負責解析查詢中的人數信息，如成人數量和兒童數量
   - 使用正則表達式和LLM進行解析
   - 能夠從總人數推斷成人和兒童數量

4. **預算解析子Agent (BudgetParserAgent)**
   - 負責解析查詢中的預算範圍，如最低價格和最高價格
   - 支持多種價格表達方式，如範圍、最低價格、最高價格和單一價格
   - 能夠處理不同的貨幣單位和價格修飾詞

5. **旅館類型解析子Agent (HotelTypeParserAgent)**
   - 負責解析查詢中的旅館類型，如飯店、民宿、度假村等
   - 使用關鍵詞匹配和LLM進行解析
   - 支持多種旅館類型的識別

6. **特殊需求解析子Agent (SpecialReqParserAgent)**
   - 負責解析查詢中的特殊需求，如旅館設施、房間設施和餐食需求
   - 使用關鍵詞匹配和LLM進行解析
   - 支持多種特殊需求的識別

7. **旅館名稱/關鍵字解析子Agent (KeywordParserAgent)**
   - 負責解析查詢中的旅館名稱和方案名稱
   - 使用正則表達式和LLM進行解析
   - 能夠判斷查詢是否為關鍵字搜索模式

8. **備品搜尋子Agent (SupplyParserAgent)**
   - 負責解析查詢中的房間備品名稱
   - 使用正則表達式和LLM進行解析
   - 能夠識別各種常見的房間備品
   - 支持多種備品搜尋表達方式

### 主查詢解析Agent (QueryParserAgent)

主查詢解析Agent負責協調各個子Agent的工作，並整合它們的解析結果。它的工作流程如下：

1. 接收用戶查詢
2. 使用OpenCC將簡體中文轉換為繁體中文
3. 確保地理資料快取已初始化
4. 創建上下文字典，用於在各個子Agent之間共享資訊
5. 依次調用各個子Agent解析查詢中的特定部分
6. 整合各個子Agent的解析結果，構建最終的解析結果
7. 返回解析結果

## 解析結果格式

解析結果為一個JSON對象，根據不同的搜尋模式有不同的格式：

### 條件搜尋模式

```json
{
    "original_query": "用戶原始查詢",
    "search_mode": "filter",
    "hotel_group_types": "旅館類型",
    "check_in": "YYYY-MM-DD",
    "check_out": "YYYY-MM-DD",
    "adults": 成人數量,
    "children": 兒童數量,
    "lowest_price": 最低價格,
    "highest_price": 最高價格,
    "county_ids": ["縣市ID1", "縣市ID2", ...],
    "district_ids": ["鄉鎮區ID1", "鄉鎮區ID2", ...],
    "hotel_facility_ids": ["設施ID1", "設施ID2", ...],
    "room_facility_ids": ["設施ID1", "設施ID2", ...],
    "has_breakfast": true/false,
    "has_lunch": true/false,
    "has_dinner": true/false,
    "special_requirements": ["需求1", "需求2", ...]
}
```

### 關鍵字搜尋模式

```json
{
    "original_query": "用戶原始查詢",
    "search_mode": "keyword",
    "hotel_keyword": "旅館名稱/關鍵字",
    "plan_keyword": "方案名稱/關鍵字",
    "check_in_start_at": "YYYY-MM-DD",
    "check_in_end_at": "YYYY-MM-DD"
}
```

### 備品搜尋模式

```json
{
    "original_query": "用戶原始查詢",
    "search_mode": "supply",
    "supply_name": "房間備品名稱"
}
```

## 使用方法

```python
from src.agents.query_parser_agent import query_parser_agent

# 解析用戶查詢
result = await query_parser_agent.run({"user_query": "我想在台北市找一家有游泳池的五星級飯店，預算5000-8000元，兩大一小，8月15日入住兩晚"})

# 獲取解析結果
parsed_query = result["parsed_query"]
```

## 擴展方法

如果需要添加新的解析功能，可以按照以下步驟進行：

1. 創建一個新的子Agent，繼承自BaseSubAgent
2. 實現_process_query方法，處理查詢中的特定部分
3. 在主查詢解析Agent中添加對新子Agent的調用
4. 在_build_parsed_query方法中添加對新解析結果的處理

## 注意事項

- 所有子Agent都使用正則表達式和LLM進行解析，如果正則表達式無法解析，則使用LLM進行解析
- 如果LLM也無法解析，則使用默認值或推斷值
- 所有解析結果都會進行驗證，確保數據的有效性
- 系統支持多種查詢模式，包括條件搜索和關鍵字搜索

## 子Agent 說明

### GuestParserAgent

人數解析子Agent，負責從用戶查詢中提取人數信息。

支持的表達方式：
- 基本表達式：如 "2個大人"、"3名成人"、"4大"、"2大2小" 等
- 家庭表達式：如 "一家三口"、"我們是五口家庭"、"我們一家四口" 等
- 混合表達式：如 "我們一家三口加上祖父母"、"我們夫妻帶著3個孩子和爺爺奶奶" 等
- 特殊情況：如 "我們是一對夫妻"、"我和妻子帶著父母旅行"、"我們全家六口人出遊" 等

解析方法：
1. 首先使用正則表達式提取家庭人數表達式
2. 檢查是否有特殊家庭成員表達（如祖父母、父母等）
3. 檢查是否有額外的兒童表達（如"還有一個小嬰兒"）
4. 使用 spaCy 進行自然語言處理，提取人數信息
5. 如果以上方法都無法解析，使用正則表達式進行基本解析
6. 如果仍然無法解析，使用默認值（2位成人，0位兒童）
