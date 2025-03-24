# 旅館推薦 Multi-Agent Chatbot 系統

基於LangGraph的旅館推薦多Agent系統，為用戶提供旅遊住宿與周邊探索的整合解決方案。

## 系統架構

本系統採用LangGraph框架實現多Agent協作，主要包含以下組件：

1. **解析類Agent群組**：由多個專門的解析Agent組成，包括：

   - 日期解析
   - 預算解析
   - 地理位置解析
   - 住客資訊解析
   - 旅館類型解析
   - 關鍵字解析
   - 特殊需求解析
   - 餐食需求解析
   - 供應商資訊解析
2. **搜索類Agent群組**：

   - 旅館搜索Agent
   - 旅館模糊搜索Agent
   - 旅館方案搜索Agent
   - 周邊景點搜索Agent
3. **回應生成Agent**：負責整合所有信息，生成最終的回應。
4. **地理資料快取**：存儲台灣縣市鄉鎮等地理資料，加速查詢解析過程。

系統工作流程如下：

```mermaid
graph TD
    A[開始<br>Start] --> B[Parse Router<br>解析路由]

    B -->|條件路由| C1[Budget Parser<br>預算解析器]
    B -->|條件路由| C2[Date Parser<br>日期解析器]
    B -->|條件路由| C3[Geo Parser<br>地理解析器]
    B -->|條件路由| C4[Food Req Parser<br>餐飲需求解析器]
    B -->|條件路由| C5[Guest Parser<br>旅客解析器]
    B -->|條件路由| C6[Hotel Type Parser<br>旅館類型解析器]
    B -->|條件路由| C7[Keyword Parser<br>關鍵字解析器]
    B -->|條件路由| C8[Special Req Parser<br>特殊需求解析器]
    B -->|條件路由| C9[Supply Parser<br>設施需求解析器]

    C1 --> D[Search Router<br>搜索路由]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    C6 --> D
    C7 --> D
    C8 --> D
    C9 --> D

    C1 -->|若有錯誤| E[Error Handler<br>錯誤處理器]
    C2 -->|若有錯誤| E
    C3 -->|若有錯誤| E
    C4 -->|若有錯誤| E
    C5 -->|若有錯誤| E
    C6 -->|若有錯誤| E
    C7 -->|若有錯誤| E
    C8 -->|若有錯誤| E
    C9 -->|若有錯誤| E

    D -->|條件路由| F1[Hotel Search<br>旅館搜索]
    D -->|條件路由| F2[Hotel Search Fuzzy<br>旅館模糊搜索]
    D -->|條件路由| F3[Hotel Search Plan<br>旅館方案搜索]

    F1 -->|完成或需重試| G[Search Results Aggregator<br>搜索結果匯總]
    F2 -->|完成或需重試| G
    F3 -->|完成或需重試| G

    F1 -->|需重試| D
    F2 -->|需重試| D
    F3 -->|需重試| D

    G --> H[LLM Agent<br>語言模型代理]
    H --> I[Response Generator<br>回應生成器]
    I --> J[Hotel Recommendation<br>旅館推薦]

    E --> Z[結束<br>End]
    D -->|若有錯誤| I

    subgraph Node Wrapper 錯誤處理
        C1 -->|異常| X[跳過節點並記錄錯誤<br>Skip Node and Log Error]
        F1 -->|異常| X
        H -->|異常| X
        X -->|返回當前狀態| Next[下一個節點<br>Next Node]
    end

    J --> Z

    classDef parser fill:#FFD1DC,stroke:#A31F34,stroke-width:2px,color:#A31F34;
    classDef search fill:#B3E5FC,stroke:#0288D1,stroke-width:2px,color:#0288D1;
    classDef generator fill:#C8E6C9,stroke:#2E7D32,stroke-width:2px,color:#2E7D32;
    classDef router fill:#FFECB3,stroke:#F57C00,stroke-width:2px,color:#F57C00;
    classDef error fill:#FFCDD2,stroke:#C62828,stroke-width:2px,color:#C62828;


    class C1,C2,C3,C4,C5,C6,C7,C8,C9 parser;
    class F1,F2,F3 search;
    class H,I,J generator;
    class B,D router;
    class E,X error;
```

## 特點

- **快速響應**：系統在5秒內提供初步回應，30秒內提供完整建議。
- **並行處理**：多個Agent並行工作，提高效率。
- **漸進式回應**：先提供初步結果，再補充詳細信息。
- **容錯機制**：處理各種異常情況，確保系統穩定性。
- **用戶友好**：提供直觀的Web界面，支持即時對話。
- **地理資料快取**：預加載台灣縣市鄉鎮資料，大幅提升查詢解析速度。

## 技術棧

- **Python 3.12**：基礎編程語言
- **LangGraph**：多Agent協作框架
- **FastAPI**：Web服務框架
- **WebSocket**：實時通信
- **Pydantic v2**：數據驗證
- **aiohttp**：異步HTTP客戶端
- **loguru**：日誌記錄
- **orjson**：高性能JSON處理
- **OpenCC**：繁簡轉換

## 安裝與運行

### 環境要求

- Python 3.12+
- 可選：OpenAI API密鑰或本地Ollama服務
- 可選：Duckling服務（用於日期解析）

### 安裝步驟

1. 克隆倉庫：

```bash
git clone https://github.com/yourusername/hotel-recommendation-system.git
cd hotel-recommendation-system
```

2. 創建虛擬環境：

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

3. 安裝依賴：

```bash
pip install -r requirements.txt
```

4. 配置環境變量：

複製 `.env.example`為 `.env`，並填寫相關配置：

```bash
cp .env.example .env
# 編輯.env文件，填寫API密鑰等信息
```

### 運行系統

```bash
python main.py
```

訪問 http://localhost:8000 即可使用系統。

## API文檔

系統提供以下API：

- `GET /`：Web界面
- `POST /api/chat`：聊天API
- `WebSocket /ws/chat/{session_id}`：WebSocket聊天

## 系統架構解析

### 目錄結構

```
├── main.py                 # 主入口文件
├── requirements.txt        # 依賴列表
├── .env                    # 環境變量
├── src/                    # 源代碼
│   ├── api/                # API模塊
│   │   ├── client.py       # API客戶端
│   │   └── services.py     # API服務
│   ├── agents/             # Agent模塊
│   │   ├── base/           # 基礎Agent類
│   │   ├── parsers/        # 解析類Agent
│   │   │   ├── budget_parser_agent.py
│   │   │   ├── date_parser_agent.py 
│   │   │   ├── food_req_parser_agent.py
│   │   │   ├── geo_parser_agent.py
│   │   │   ├── guest_parser_agent.py
│   │   │   ├── hotel_type_parser_agent.py
│   │   │   ├── keyword_parser_agent.py
│   │   │   ├── special_req_parser_agent.py
│   │   │   └── supply_parser_agent.py
│   │   ├── search/         # 搜索類Agent
│   │   │   ├── hotel_search_agent.py
│   │   │   ├── hotel_search_fuzzy_agent.py
│   │   │   ├── hotel_search_plan_agent.py
│   │   │   └── poi_search_agent.py
│   │   └── generators/     # 生成類Agent
│   │       ├── hotel_recommendation_agent.py
│   │       ├── llm_agent.py
│   │       └── response_generator_agent.py
│   ├── cache/              # 快取模塊
│   │   └── geo_cache.py    # 地理資料快取
│   ├── graph/              # LangGraph模塊
│   │   ├── workflow.py     # 工作流定義
│   │   └── merge_func.py   # 狀態合併函數
│   ├── models/             # 數據模型
│   │   └── schemas.py      # 數據結構定義
│   ├── services/           # 服務模塊
│   ├── utils/              # 工具模塊
│   ├── web/                # Web模塊
│   │   ├── app.py          # FastAPI應用
│   │   ├── websocket.py    # WebSocket處理
│   │   ├── static/         # 靜態文件
│   │   └── templates/      # HTML模板
│   └── config.py           # 配置模塊
```

### 核心模塊說明

#### 1. 配置管理 (`src/config.py`)

包含系統所有配置項目，主要分為：

- API配置：API端點、密鑰等
- LLM配置：LLM提供商選擇
- Ollama配置：本地LLM模型設定
- 系統配置：超時、重試次數等
- FastAPI配置：主機、端口等

#### 2. Agent架構

系統採用多層次Agent架構，每個Agent專注於特定任務：

**解析類Agent**：分別負責解析不同類型的用戶需求：

- 日期解析：處理入住/退房日期
- 預算解析：處理價格預算範圍
- 地理位置解析：處理地點資訊
- 住客解析：處理旅客人數、組成等信息
- 旅館類型解析：處理旅館類型偏好
- 關鍵字解析：處理其他關鍵詞信息
- 特殊需求解析：處理特殊要求
- 餐食需求解析：處理餐食相關需求
- 供應商解析：處理特定供應商偏好

**搜索類Agent**：

- 旅館搜索：基本旅館搜索功能
- 旅館模糊搜索：處理不完整條件下的搜索 (未實現)
- 旅館方案搜索：搜索特定方案 (未實現)
- 景點搜索：搜索周邊景點 (半實現 | 取得旅館座標後轉請求 google api可獲得景點)

**生成類Agent**：

- LLM代理：處理LLM響應
- 回應生成器：生成結構化響應
- 旅館推薦：生成最終推薦

#### 3. 地理資料快取 (`src/cache/geo_cache.py`)

預加載並快取台灣的地理資料，減少運行時查詢負擔：

- 縣市資料
- 鄉鎮區資料
- 縣市對應鄉鎮資料

#### 4. 工作流程定義 (`src/graph/workflow.py`)

使用LangGraph框架定義整個系統的工作流程：

- 定義節點之間的關係
- 處理並行任務
- 管理條件分支
- 錯誤處理與重試機制

#### 5. Web界面 (`src/web/`)

提供用戶界面和API端點：

- FastAPI應用服務
- WebSocket實時通信
- 靜態資源和模板

## 開發進度

### 已完成

- [X] 基礎框架設定與專案結構
- [X] 配置管理系統
- [X] LLM服務整合 (OpenAI & Ollama)
- [X] Agent定義與實現
  - [X] 解析類Agent群組
  - [X] 搜索類Agent群組
  - [X] 回應生成Agent
- [X] 地理資料快取系統
- [X] LangGraph工作流定義
- [X] FastAPI後端服務
- [X] WebSocket支援
- [X] 實時進度回饋

### 進行中

- [ ] 測試與性能優化
- [ ] 各類解析調優
- [ ] 更多API整合
- [ ] 文檔完善

## 許可證

MIT
