"""
WebSocket處理程序，用於處理與前端的實時通信
"""

import asyncio
import json
import uuid
from typing import Any

import orjson
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from src.graph.workflow import run_workflow
from src.models.schemas import StreamChatResponse
from src.services.conversation_service import ConversationService


class ConnectionManager:
    """WebSocket連接管理器"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.conversation_service = ConversationService()

    async def connect(self, websocket: WebSocket) -> str:
        """建立WebSocket連接"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket連接建立: {connection_id}")
        return connection_id

    def disconnect(self, connection_id: str) -> None:
        """關閉WebSocket連接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket連接關閉: {connection_id}")

    async def send_message(self, connection_id: str, message: str) -> None:
        """發送消息到指定連接"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        """廣播消息到所有連接"""
        for connection_id, websocket in self.active_connections.items():
            await websocket.send_text(message)

    async def send_stream_response(self, connection_id: str, response: StreamChatResponse) -> None:
        """發送流式回應"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(orjson.dumps(response.model_dump()).decode("utf-8"))


# 創建連接管理器實例
manager = ConnectionManager()


async def handle_websocket_connection(websocket: WebSocket) -> None:
    """處理WebSocket連接"""
    connection_id = await manager.connect(websocket)
    conversation_id = str(uuid.uuid4())

    try:
        # 發送歡迎消息
        welcome_response = StreamChatResponse(
            message_chunk="您好！我是旅館推薦助手。請告訴我您想去哪裡旅行，以及您對住宿有什麼特別的要求？",
            conversation_id=conversation_id,
            is_complete=True,
        )
        await manager.send_stream_response(connection_id, welcome_response)

        # 處理消息
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            logger.info(f"收到用戶消息: {user_message}")

            # 保存用戶消息
            await manager.conversation_service.add_message(conversation_id, "user", user_message)

            # 定義進度回調函數
            async def progress_callback(
                stage: str, geo_data: dict[str, Any] | None = None, message: str | None = None
            ) -> None:
                """處理進度回調"""
                response = StreamChatResponse(conversation_id=conversation_id, is_complete=False, stage=stage)

                # 根據階段設置不同的消息
                if stage == "parse_query":
                    response.message_chunk = "正在分析您的需求..."
                elif stage == "geo_parse" and geo_data:
                    response.geo_data = geo_data
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
                        response.message_chunk = f"已識別到的地理位置：\n{' | '.join(parts)}"
                    else:
                        response.message_chunk = "正在處理地理位置信息..."
                elif stage == "search_hotels":
                    response.message_chunk = "正在搜索符合條件的旅館..."
                elif stage == "search_pois":
                    response.message_chunk = "正在查找周邊景點和設施..."
                elif stage == "initial_response" and message:
                    response.message_chunk = message
                elif stage == "final_response":
                    response.message_chunk = "正在生成最終回應..."
                elif stage == "error" and message:
                    response.message_chunk = f"處理過程中遇到問題: {message}"
                    response.error = message

                await manager.send_stream_response(connection_id, response)

            # 處理用戶查詢
            try:
                # 運行工作流
                result = await run_workflow(user_message, progress_callback)

                # 獲取回應
                assistant_message = result.get("response", "")
                if not assistant_message and "error" in result:
                    assistant_message = f"很抱歉，處理您的請求時遇到了問題: {result['error']}"

                # 保存助手消息
                await manager.conversation_service.add_message(conversation_id, "assistant", assistant_message)

                # 分段發送回應
                chunks = split_message_into_chunks(assistant_message)
                for i, chunk in enumerate(chunks):
                    is_last_chunk = i == len(chunks) - 1
                    response = StreamChatResponse(
                        message_chunk=chunk,
                        conversation_id=conversation_id,
                        is_complete=is_last_chunk,
                    )
                    await manager.send_stream_response(connection_id, response)
                    if not is_last_chunk:
                        await asyncio.sleep(0.1)  # 添加短暫延遲以模擬打字效果

            except Exception as e:
                logger.error(f"處理消息時發生錯誤: {e!s}")
                error_response = StreamChatResponse(
                    message_chunk=f"很抱歉，處理您的請求時發生了錯誤: {e!s}",
                    conversation_id=conversation_id,
                    is_complete=True,
                    error=str(e),
                )
                await manager.send_stream_response(connection_id, error_response)

    except WebSocketDisconnect:
        manager.disconnect(connection_id)
        logger.info(f"WebSocket連接斷開: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket處理時發生錯誤: {e!s}")
        manager.disconnect(connection_id)


def split_message_into_chunks(message: str, max_chunk_size: int = 100) -> list[str]:
    """將消息分割成多個塊"""
    # 按句子分割
    sentences = []
    current_sentence = ""

    for char in message:
        current_sentence += char
        if char in ["。", "！", "？", ".", "!", "?", "\n"] and current_sentence.strip():
            sentences.append(current_sentence)
            current_sentence = ""

    if current_sentence.strip():
        sentences.append(current_sentence)

    # 組合成適當大小的塊
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    # 如果沒有分塊，返回原始消息
    if not chunks:
        return [message]

    return chunks
