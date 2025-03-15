"""
FastAPI 應用，提供Web界面和API
"""

import asyncio
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from src.cache.geo_cache import geo_cache
from src.graph.workflow import run_workflow
from src.utils.geo_parser import geo_parser
from src.web.websocket import ws_manager

# 創建FastAPI應用
app = FastAPI(
    title="旅館推薦 Multi-Agent Chatbot", description="基於 LangGraph 的旅館推薦多 Agent 系統", version="1.0.0"
)

# 掛載靜態文件
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# 設置模板
templates = Jinja2Templates(directory="src/web/templates")

# 存儲對話歷史
conversation_history: dict[str, list[dict[str, Any]]] = {}

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """應用啟動時執行的事件"""
    logger.info("初始化應用...")

    # 初始化地理資料快取
    await geo_cache.initialize()

    # 預先載入 spaCy 中文模型
    await geo_parser.preload_model()

    # 初始化地理名稱解析器
    await geo_parser.initialize()


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    """首頁"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def chat(message: dict[str, Any]):
    """聊天 API"""
    try:
        # 獲取對話 ID
        conversation_id = message.get("conversation_id")
        if not conversation_id:
            conversation_id = str(asyncio.get_event_loop().time())

        # 初始化對話歷史
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []

        # 添加用戶消息
        conversation_history[conversation_id].append(
            {"role": "user", "content": message.get("user_query", ""), "timestamp": asyncio.get_event_loop().time()}
        )

        # 運行工作流
        result = await run_workflow(
            {
                "user_query": message.get("user_query", ""),
                "context": message.get("context", {}),
                "conversation_id": conversation_id,
            }
        )

        # 添加系統回應
        if "error" in result:
            conversation_history[conversation_id].append(
                {"role": "system", "content": f"錯誤: {result['error']}", "timestamp": asyncio.get_event_loop().time()}
            )
        else:
            conversation_history[conversation_id].append(
                {
                    "role": "assistant",
                    "content": result.get("response", {}).get("message", ""),
                    "timestamp": asyncio.get_event_loop().time(),
                }
            )

        return {"conversation_id": conversation_id, "response": result}
    except Exception as e:
        logger.error(f"處理聊天請求失敗: {e}")
        return {"error": str(e)}


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket 聊天端點"""
    try:
        # 建立連接
        await ws_manager.connect(websocket, conversation_id)

        # 初始化對話歷史
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []

        # 發送歡迎消息
        await ws_manager.broadcast_chat_message(
            conversation_id,
            {
                "role": "assistant",
                "content": "您好！請告訴我您的旅館需求，例如地點、日期、人數和預算等。",
                "timestamp": asyncio.get_event_loop().time(),
            },
        )

        while True:
            try:
                # 接收消息
                message = await websocket.receive_json()
                logger.info(f"收到WebSocket消息: {message}")

                # 獲取用戶查詢 - 同時支持message和user_query字段
                user_query = message.get("user_query", "")
                if not user_query:
                    user_query = message.get("message", "")

                # 如果沒有用戶查詢，發送錯誤提示
                if not user_query:
                    logger.warning("收到空的用戶查詢")
                    await ws_manager.broadcast_chat_message(
                        conversation_id,
                        {
                            "role": "system",
                            "content": "請輸入您的旅遊需求，例如：'我想在台北找間飯店，2大1小，預算3000以內'",
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                    )
                    continue

                # 將用戶消息發送回前端顯示
                await ws_manager.broadcast_chat_message(
                    conversation_id,
                    {
                        "role": "user",
                        "content": user_query,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                )

                # 添加用戶消息到對話歷史
                conversation_history[conversation_id].append(
                    {"role": "user", "content": user_query, "timestamp": asyncio.get_event_loop().time()}
                )

                # 運行工作流
                logger.info(f"開始處理用戶查詢: {user_query}")
                result = await run_workflow(
                    {
                        "user_query": user_query,
                        "context": message.get("context", {}),
                        "conversation_id": conversation_id,
                    }
                )

                # 發送回應
                if "error" in result:
                    logger.error(f"工作流執行錯誤: {result['error']}")
                    await ws_manager.broadcast_chat_message(
                        conversation_id,
                        {
                            "role": "system",
                            "content": f"處理您的請求時發生錯誤: {result['error']}",
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                    )
                else:
                    # 添加助手回應到對話歷史
                    if "response" in result and "message" in result["response"]:
                        assistant_message = result["response"]["message"]
                        conversation_history[conversation_id].append(
                            {
                                "role": "assistant",
                                "content": assistant_message,
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        )

                        # 發送助手回應給前端顯示
                        await ws_manager.broadcast_chat_message(
                            conversation_id,
                            {
                                "role": "assistant",
                                "content": assistant_message,
                                "timestamp": asyncio.get_event_loop().time(),
                            },
                        )

                    # 發送完整回應
                    logger.info("發送工作流處理結果")
                    await websocket.send_json({"type": "response", "data": result})

            except WebSocketDisconnect:
                logger.info(f"WebSocket連接斷開: {conversation_id}")
                break
            except Exception as e:
                logger.error(f"處理WebSocket消息時發生錯誤: {e}")
                await ws_manager.broadcast_chat_message(
                    conversation_id,
                    {
                        "role": "system",
                        "content": f"處理您的請求時發生錯誤: {e!s}",
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                )

    except Exception as e:
        logger.error(f"WebSocket連接處理失敗: {e}")
    finally:
        # 斷開連接
        ws_manager.disconnect(conversation_id)


@app.post("/api/chat/v2")
async def chat_endpoint(data: dict):
    """
    聊天 API 端點 (v2 版本)

    Args:
        data: 請求數據

    Returns:
        回應數據
    """
    try:
        return await run_workflow(data)
    except Exception as e:
        logger.error(f"API 處理錯誤: {e}")
        return {"error": str(e)}
