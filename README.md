# 旅館推薦 Multi-Agent Chatbot 系統

## 項目概述

本項目是一個基於 Multi-Agent 架構的旅館推薦聊天機器人系統，旨在為用戶提供旅遊住宿與周邊探索的整合解決方案。
系統能夠在 5 秒內回應用戶的初步查詢，並在 30 秒內提供完整建議。

## 技術架構

目前正在評估以下 Multi-Agent 框架，以選擇最適合的技術方案：

- LangGraph
- LlamaIndex
- CrewAI
- Swarms

這些框架將結合 aiohttp 進行非同步 API 請求，以實現高效的並行處理和資源調度。

### 主要特點

- 快速響應：系統在 5 秒內提供初步回應
- 漸進式結果展示：在完整結果準備好之前提供即時反饋
- 多 Agent 協作：各 Agent 負責不同任務，協同工作提供完整解決方案
- 容錯機制：處理 API 請求失敗和超時情況

## 項目結構

```plaintext
.
├── README.md                 # 項目說明文檔
├── requirements.txt          # 依賴包列表
├── main.py                   # 主程序入口
├── config.py                 # 配置文件
├── agents/                   # Agent 定義
│   ├── __init__.py
│   ├── coordinator.py        # 協調者 Agent
│   ├── hotel_agent.py        # 旅館推薦 Agent
│   ├── poi_agent.py          # 周邊景點 Agent
│   └── response_agent.py     # 回應生成 Agent
├── api/                      # API 相關
│   ├── __init__.py
│   ├── client.py             # API 客戶端
│   └── schemas.py            # API 數據模型
├── utils/                    # 工具函數
│   ├── __init__.py
│   └── helpers.py            # 輔助函數
└── tests/                    # 測試代碼
    ├── __init__.py
    └── test_agents.py        # Agent 測試

```

## 開發進度

- [X] 基本框架建構
- [ ] 框架定案|實現 Multi-Agent 框架測試評比
- [ ] API 客戶端實現
- [ ] Agent 定義與實現
- [ ] 協調機制設計
- [ ] 漸進式回應策略
- [ ] 容錯機制
- [ ] 用戶交互設計
- [ ] 測試與優化

## 安裝與運行

### 環境要求

- Python 3.12
- 依賴包見 requirements.txt (框架訂案後提供)

### 安裝步驟

```bash
# clone 項目
git clone https://github.com/coseto6125/hotel-multiagent.git
cd hotel-multiagent

# 安裝依賴
pip install-requirements.txt #框架定案後提供

# 運行系統
python main.py
```

## Agent 架構說明

### 協調者 Agent (Coordinator)

負責接收用戶查詢，分配任務給其他 Agent，並整合結果。

### 旅館推薦 Agent (Hotel Agent)

負責根據用戶需求查詢旅館信息，提供合適的住宿選項。

### 周邊景點 Agent (POI Agent)

負責查詢旅館周邊的景點、餐廳等信息，提供周邊探索建議。

### 回應生成 Agent (Response Agent)

負責將各 Agent 的結果整合成自然、流暢的回應，提供給用戶。

## API 使用說明

系統使用以下 API 獲取旅館和周邊信息：

- 旅宿基礎參數 API
- 旅館信息 API
- 查詢周邊地標 API

詳細 API 文檔見：[https://raccoonai-agents-api.readme.io/reference](https://raccoonai-agents-api.readme.io/reference)
