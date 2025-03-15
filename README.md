# 旅館推薦 Multi-Agent Chatbot 系統

基於LangGraph的旅館推薦多Agent系統，為用戶提供旅遊住宿與周邊探索的整合解決方案。

## 系統架構

本系統採用LangGraph框架實現多Agent協作，主要包含以下組件：

1. **查詢解析Agent**：負責解析用戶的自然語言查詢，提取關鍵參數。
2. **旅館搜索Agent**：負責根據解析後的參數搜索符合條件的旅館。
3. **周邊地標搜索Agent**：負責搜索旅館周邊的景點、餐廳和交通信息。
4. **回應生成Agent**：負責整合所有信息，生成最終的回應。
5. **地理資料快取**：存儲台灣縣市鄉鎮等地理資料，加速查詢解析過程。

系統工作流程如下：

```
用戶查詢 -> 查詢解析(使用地理資料快取) -> 旅館搜索 -> 初步回應 -> 周邊地標搜索 -> 最終回應
```

## 特點

- **快速響應**：系統在5秒內提供初步回應，30秒內提供完整建議。
- **並行處理**：多個Agent並行工作，提高效率。
- **漸進式回應**：先提供初步結果，再補充詳細信息。
- **容錯機制**：處理各種異常情況，確保系統穩定性。
- **用戶友好**：提供直觀的Web界面，支持實時對話。
- **地理資料快取**：預加載台灣縣市鄉鎮資料，大幅提升查詢解析速度。

## 技術棧

- **Python 3.13**：基礎編程語言
- **LangGraph**：多Agent協作框架
- **FastAPI**：Web服務框架
- **WebSocket**：實時通信
- **Pydantic**：數據驗證
- **aiohttp**：異步HTTP客戶端
- **loguru**：日誌記錄
- **orjson**：高性能JSON處理
- **Redis/SQLite**：地理資料快取存儲

## 安裝與運行

### 環境要求

- Python 3.13+
- 可選：OpenAI API密鑰或本地Ollama服務

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
- `WebSocket /ws/chat/{conversation_id}`：WebSocket聊天

## 開發指南

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
│   │   ├── base_agent.py   # 基礎Agent類
│   │   ├── query_parser_agent.py    # 查詢解析Agent
│   │   ├── hotel_search_agent.py    # 旅館搜索Agent
│   │   ├── poi_search_agent.py      # 周邊地標搜索Agent
│   │   └── response_generator_agent.py  # 回應生成Agent
│   ├── cache/              # 快取模塊
│   │   ├── geo_cache.py    # 地理資料快取
│   │   └── cache_manager.py # 快取管理器
│   ├── graph/              # LangGraph模塊
│   │   └── workflow.py     # 工作流定義
│   ├── models/             # 數據模型
│   │   └── schemas.py      # 數據結構定義
│   ├── services/           # 服務模塊
│   │   └── llm_service.py  # LLM服務
│   ├── utils/              # 工具模塊
│   ├── web/                # Web模塊
│   │   ├── app.py          # FastAPI應用
│   │   ├── static/         # 靜態文件
│   │   └── templates/      # HTML模板
│   └── config.py           # 配置模塊
└── tests/                  # 測試模塊
```

### 擴展指南

1. **添加新的Agent**：

   - 在 `src/agents/`目錄下創建新的Agent類
   - 繼承 `BaseAgent`類
   - 實現 `_process`方法
2. **修改工作流**：

   - 在 `src/graph/workflow.py`中修改工作流定義
3. **添加新的API服務**：

   - 在 `src/api/services.py`中添加新的API服務類

## 開發進度

### 基本框架建構

- [X] 專案結構設定
- [X] 配置管理系統
- [X] 日誌系統
- [X] 環境變數設定

### LLM 服務整合

- [X] OpenAI 整合
- [X] Ollama 整合
- [X] 非同步回應生成

### Agent 定義與實現

- [X] 查詢解析 Agent
- [ ] 旅館搜索 Agent
- [ ] 景點搜索 Agent
- [ ] 回應生成 Agent

### 快取系統實現

- [ ] 地理資料快取設計
- [ ] 縣市鄉鎮資料預加載
- [ ] 快取更新機制
- [ ] 快取查詢優化

### LangGraph 工作流實現

- [X] 工作流架構設計
- [ ] 節點間狀態傳遞
- [ ] 條件分支處理
- [ ] 錯誤處理機制

### API 客戶端實現

- [ ] 旅館資料 API 整合
- [ ] 景點資料 API 整合
- [ ] 請求重試機制
- [ ] 資料快取策略

### FastAPI 後端服務

- [X] 基本路由設定
- [X] WebSocket 支援
- [ ] 請求處理與回應生成
- [ ] 錯誤處理與日誌記錄

### 漸進式回應策略

- [ ] 初步回應生成
- [ ] 流式回應處理
- [ ] 超時處理機制

### 測試與優化

- [X] 單元測試框架設定
- [ ] Agent 功能測試
- [ ] 工作流整合測試
- [ ] 效能優化


## 貢獻指南

歡迎提交Pull Request或Issue。

## 許可證

MIT
