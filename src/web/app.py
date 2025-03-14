"""
FastAPI 應用，提供Web界面和API
"""

import asyncio
import uuid
from typing import Any

import orjson
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from src.config import config
from src.graph.workflow import run_workflow
from src.models.schemas import ChatRequest, ChatResponse, StreamChatResponse

# 創建FastAPI應用
app = FastAPI(title="旅館推薦系統", description="旅館推薦 Multi-Agent Chatbot 系統", version="1.0.0")

# 掛載靜態文件
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# 設置模板
templates = Jinja2Templates(directory="src/web/templates")

# 存儲活躍的WebSocket連接
active_connections: dict[str, WebSocket] = {}

# 存儲對話歷史
conversation_history: dict[str, list[dict[str, Any]]] = {}


@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    """首頁"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天API"""
    # TODO: 實現聊天API
    message = request.message
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # 存儲用戶消息
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []

    conversation_history[conversation_id].append({"role": "user", "content": message})

    # 運行工作流
    try:
        # 運行工作流
        result = await run_workflow(message)

        # 獲取回應
        response = result.get("response", "")
        if not response and "error" in result:
            response = f"抱歉，發生錯誤: {result['error']}"
        elif not response:
            response = "抱歉，我無法處理您的請求。請嘗試重新表述您的問題。"

        # 存儲助手回應
        conversation_history[conversation_id].append({"role": "assistant", "content": response})

        return ChatResponse(message=response, conversation_id=conversation_id, is_complete=True)
    except Exception as e:
        logger.error(f"處理聊天請求時發生錯誤: {e!s}")
        return ChatResponse(
            message=f"抱歉，處理您的請求時發生錯誤: {e!s}", conversation_id=conversation_id, is_complete=True
        )


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """WebSocket聊天"""
    # TODO: 實現WebSocket聊天
    await websocket.accept()

    # 生成新的對話ID（如果需要）
    if not conversation_id or conversation_id == "new":
        conversation_id = str(uuid.uuid4())

    # 存儲WebSocket連接
    active_connections[conversation_id] = websocket

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = orjson.loads(data)
            message = message_data.get("message", "")

            # 存儲用戶消息
            if conversation_id not in conversation_history:
                conversation_history[conversation_id] = []

            conversation_history[conversation_id].append({"role": "user", "content": message})

            try:
                # 運行工作流
                task = asyncio.create_task(run_workflow(message))

                # 等待初步回應（最多5秒）
                initial_response_timeout = config.system.initial_response_timeout
                try:
                    # 等待一小段時間，讓工作流有機會生成初步回應
                    await asyncio.sleep(initial_response_timeout)

                    # 檢查工作流是否已完成
                    if task.done():
                        result = task.result()
                    else:
                        # 發送初步回應
                        initial_response = "我正在為您搜索符合條件的旅館和周邊景點，請稍候..."
                        await websocket.send_text(
                            orjson.dumps(
                                StreamChatResponse(
                                    message_chunk=initial_response, conversation_id=conversation_id, is_complete=False
                                ).dict()
                            ).decode("utf-8")
                        )

                        # 等待工作流完成
                        complete_response_timeout = config.system.complete_response_timeout
                        try:
                            result = await asyncio.wait_for(task, timeout=complete_response_timeout)
                        except TimeoutError:
                            # 如果工作流仍未完成，發送超時消息
                            await websocket.send_text(
                                orjson.dumps(
                                    StreamChatResponse(
                                        message_chunk="抱歉，處理您的請求需要更長時間。請稍後再試或重新表述您的問題。",
                                        conversation_id=conversation_id,
                                        is_complete=True,
                                    ).dict()
                                ).decode("utf-8")
                            )
                            continue
                except TimeoutError:
                    # 如果無法在指定時間內獲得初步回應，發送等待消息
                    await websocket.send_text(
                        orjson.dumps(
                            StreamChatResponse(
                                message_chunk="正在處理您的請求，請稍候...",
                                conversation_id=conversation_id,
                                is_complete=False,
                            ).dict()
                        ).decode("utf-8")
                    )

                    # 等待工作流完成
                    complete_response_timeout = config.system.complete_response_timeout
                    try:
                        result = await asyncio.wait_for(task, timeout=complete_response_timeout)
                    except TimeoutError:
                        # 如果工作流仍未完成，發送超時消息
                        await websocket.send_text(
                            orjson.dumps(
                                StreamChatResponse(
                                    message_chunk="抱歉，處理您的請求需要更長時間。請稍後再試或重新表述您的問題。",
                                    conversation_id=conversation_id,
                                    is_complete=True,
                                ).dict()
                            ).decode("utf-8")
                        )
                        continue

                # 獲取回應
                response = result.get("response", "")
                if not response and "error" in result:
                    response = f"抱歉，發生錯誤: {result['error']}"
                elif not response:
                    response = "抱歉，我無法處理您的請求。請嘗試重新表述您的問題。"

                # 存儲助手回應
                conversation_history[conversation_id].append({"role": "assistant", "content": response})

                # 發送最終回應
                await websocket.send_text(
                    orjson.dumps(
                        StreamChatResponse(
                            message_chunk=response, conversation_id=conversation_id, is_complete=True
                        ).dict()
                    ).decode("utf-8")
                )
            except Exception as e:
                logger.error(f"處理WebSocket消息時發生錯誤: {e!s}")
                await websocket.send_text(
                    orjson.dumps(
                        StreamChatResponse(
                            message_chunk=f"抱歉，處理您的請求時發生錯誤: {e!s}",
                            conversation_id=conversation_id,
                            is_complete=True,
                        ).dict()
                    ).decode("utf-8")
                )
    except WebSocketDisconnect:
        # 移除WebSocket連接
        if conversation_id in active_connections:
            del active_connections[conversation_id]
    except Exception as e:
        logger.error(f"WebSocket連接發生錯誤: {e!s}")
        # 移除WebSocket連接
        if conversation_id in active_connections:
            del active_connections[conversation_id]
