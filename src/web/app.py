"""
FastAPI 應用，提供Web界面和API
"""

import asyncio
import random
import uuid
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
    # 生成新的session_id
    session_id = str(uuid.uuid4())

    # 將session_id傳給前端，但不設置為cookie
    return templates.TemplateResponse("index.html", {"request": request, "session_id": session_id})


@app.post("/api/chat")
async def chat(message: dict[str, Any], request: Request):
    """聊天 API"""
    try:
        # 獲取session_id，從請求中獲取
        async_time = asyncio.get_event_loop().time
        session_id = message.get("session_id", str(uuid.uuid4()))

        # 運行工作流
        result = await run_workflow(
            {
                "user_query": message.get("user_query", ""),
                "context": message.get("context", {}),
                "session_id": session_id,
            }
        )

        return {"session_id": session_id, "response": result}
    except Exception as e:
        logger.error(f"處理聊天請求失敗: {e}")
        return {"error": str(e)}


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 聊天端點 - 使用查詢參數傳遞session_id"""
    async_time = asyncio.get_event_loop().time

    # 從查詢參數獲取session_id
    session_id = websocket.query_params.get("session_id", str(uuid.uuid4()))

    try:
        # 先建立連接，這必須是第一步
        await ws_manager.connect(websocket, session_id)
        logger.info(f"WebSocket連接已建立，session_id: {session_id}")

        # 發送歡迎消息
        await send_chat_message(session_id, "您好！請告訴我您的旅館需求，要包含地點、日期、人數和預算喔！")

        while True:
            try:
                # 接收消息
                message = await websocket.receive_json()
                logger.info(f"收到WebSocket消息: {message}")

                # 處理心跳回應
                if message.get("type") == "heartbeat_response":
                    logger.debug(f"收到心跳回應: {session_id}")
                    continue

                # 獲取用戶查詢 - 同時支持message和user_query字段
                user_query = message.get("user_query", "")
                if not user_query:
                    user_query = message.get("message", "")

                # 如果沒有用戶查詢，發送錯誤提示
                if not user_query:
                    logger.warning("收到空的用戶查詢")
                    await send_chat_message(
                        session_id,
                        "請輸入您的旅遊需求，例如：'我想在台北找間飯店，2大1小，預算3000以內'",
                        role="system",
                    )
                    continue

                # 將用戶消息發送回前端顯示
                await send_chat_message(session_id, user_query, role="user")

                # 運行工作流
                logger.info(f"開始處理用戶查詢: {user_query}")

                # 定義進度回調函數
                async def progress_callback(
                    stage: str, geo_data: dict[str, Any] | None = None, message: str | None = None
                ) -> None:
                    """處理進度回調"""
                    # 根據階段設置不同的消息
                    logger.info(f"進度回調: {stage}")
                    if stage == "parse_query":
                        content = "正在分析您的需求..."
                    elif stage == "geo_parse" and geo_data:
                        locations = geo_data.get("locations", [])
                        county = geo_data.get("county")
                        district = geo_data.get("district")

                        location_text = ""
                        if locations:
                            location_text = f"地點：{', '.join(locations)}"

                        area_text = ""
                        if county or district:
                            parts = []
                            if county:
                                parts.append(county)
                            if district:
                                parts.append(district)
                            area_text = f"區域：{' '.join(parts)}"

                        if location_text or area_text:
                            parts = []
                            if area_text:
                                parts.append(area_text)
                            if location_text:
                                parts.append(location_text)
                            content = f"已識別到的地理位置：\n{' | '.join(parts)}"
                        else:
                            content = "正在處理地理位置信息..."
                    elif stage == "search_hotels":
                        content = "正在搜索符合條件的旅館..."
                    elif stage == "search_pois":
                        content = "正在查找周邊景點和設施..."
                    elif stage == "initial_response" and message:
                        content = message
                    elif stage == "final_response":
                        content = "已完成旅館推薦"
                    elif stage == "error" and message:
                        content = f"處理過程中遇到問題: {message}"
                    else:
                        content = f"處理中... ({stage})"

                    # 發送進度消息
                    await send_chat_message(session_id, content, role="system", is_progress=True)

                result = await run_workflow(
                    {
                        "user_query": user_query,
                        "context": message.get("context", {}),
                        "session_id": session_id,
                    },
                    progress_callback,
                )

                # 發送回應
                if result.get("err_msg"):
                    logger.warning(f"工作流執行警告app: {result['err_msg']}")

                    # 開始流式回應
                    await websocket.send_json(
                        {
                            "type": "chat_message",
                            "data": {"role": "assistant_stream_start", "content": "", "timestamp": async_time()},
                        }
                    )

                    # 獲取錯誤消息
                    error_message = result.get("err_msg", "很抱歉，系統繁忙，請再試一次！")

                    # 如果錯誤消息是字符串，轉換為列表
                    if isinstance(error_message, str):
                        error_message = [error_message]

                    # 逐字符發送錯誤消息
                    full_message = ""
                    for msg in error_message:
                        for char in msg:
                            full_message += char
                            # 發送流式消息
                            await websocket.send_json(
                                {
                                    "type": "chat_message",
                                    "data": {"role": "assistant_stream", "content": char, "timestamp": async_time()},
                                }
                            )
                            # 模擬打字速度，隨機延遲
                            await asyncio.sleep(0.02 + 0.01 * random.random())

                        # 消息之間添加換行
                        if msg != error_message[-1]:
                            full_message += "\n"
                            await websocket.send_json(
                                {
                                    "type": "chat_message",
                                    "data": {"role": "assistant_stream", "content": "\n", "timestamp": async_time()},
                                }
                            )
                            await asyncio.sleep(0.3)

                    # 結束流式回應
                    await websocket.send_json(
                        {
                            "type": "chat_message",
                            "data": {"role": "assistant_stream_end", "content": "", "timestamp": async_time()},
                        }
                    )

                elif result.get("error"):
                    logger.error(f"工作流執行錯誤app: {result['error']}")
                    await send_chat_message(
                        session_id, f"處理您的請求時發生錯誤: {result.get('err_msg', '未知錯誤')}", role="system"
                    )
                else:
                    # 如果回應狀態不是成功，發送消息
                    if result["response"]["status"] != "success":
                        assistant_message = result["response"]["message"]

                        # 開始流式回應
                        await websocket.send_json(
                            {
                                "type": "chat_message",
                                "data": {"role": "assistant_stream_start", "content": "", "timestamp": async_time()},
                            }
                        )

                        # 逐字符發送回應
                        for char in assistant_message:
                            # 發送流式消息
                            await websocket.send_json(
                                {
                                    "type": "chat_message",
                                    "data": {"role": "assistant_stream", "content": char, "timestamp": async_time()},
                                }
                            )
                            # 模擬打字速度，隨機延遲
                            await asyncio.sleep(0.05 + 0.07 * random.random())

                        # 結束流式回應
                        await websocket.send_json(
                            {
                                "type": "chat_message",
                                "data": {"role": "assistant_stream_end", "content": "", "timestamp": async_time()},
                            }
                        )

                    # 發送完整回應
                    logger.info("工作流處理完成")
                    return

            except WebSocketDisconnect:
                logger.info(f"WebSocket連接斷開: {session_id}")
                break
            except Exception as e:
                logger.error(f"處理WebSocket消息時發生錯誤: {e}")
                await send_chat_message(session_id, f"處理您的請求時發生錯誤: {e!s}", role="system")

    except Exception as e:
        logger.error(f"WebSocket連接處理失敗: {e}")
    finally:
        # 斷開連接
        ws_manager.disconnect(session_id)
        logger.info(f"WebSocket連接已關閉: {session_id}")


async def send_chat_message(session_id: str, content: str, role: str = "assistant", is_progress: bool = False) -> None:
    """
    發送聊天消息的抽象函數

    Args:
        session_id: 會話ID
        role: 消息角色 (user, assistant, system)
        content: 消息內容
        is_progress: 是否為進度消息
    """
    async_time = asyncio.get_event_loop().time
    await ws_manager.broadcast_chat_message(
        session_id,
        {
            "role": role,
            "content": content,
            "timestamp": async_time(),
            "is_progress": is_progress,
        },
    )
