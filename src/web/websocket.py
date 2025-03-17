"""
WebSocket 管理器模組

負責管理 WebSocket 連接和消息廣播。
"""

import asyncio
from typing import Any

import orjson
from fastapi import WebSocket
from loguru import logger

from src.models.schemas import StreamChatResponse


class WebSocketManager:
    """WebSocket 管理器類別"""

    def __init__(self):
        """初始化 WebSocket 管理器"""
        self.active_connections: dict[str, WebSocket] = {}
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        """接受 WebSocket 連接"""
        # 確保先接受連接
        await websocket.accept()
        self.active_connections[conversation_id] = websocket
        logger.info(f"WebSocket 連接已建立: {conversation_id}")

        # 啟動心跳任務
        self.start_heartbeat(conversation_id)

    def disconnect(self, conversation_id: str):
        """關閉 WebSocket 連接"""
        if conversation_id in self.active_connections:
            # 停止心跳任務
            self.stop_heartbeat(conversation_id)
            # 移除連接
            del self.active_connections[conversation_id]
            logger.info(f"WebSocket 連接已關閉: {conversation_id}")

    async def broadcast_progress(self, conversation_id: str, progress: dict[str, Any]):
        """廣播進度更新"""
        if conversation_id not in self.active_connections:
            return

        try:
            await self.active_connections[conversation_id].send_json({"type": "progress", "data": progress})
            logger.debug(f"進度更新已發送: {conversation_id}")
        except Exception as e:
            logger.error(f"發送進度更新失敗: {e}")
            # 連接可能已斷開，移除連接
            self.disconnect(conversation_id)

    async def broadcast_chat_message(self, conversation_id: str, message: dict[str, Any]):
        """廣播聊天消息"""
        if conversation_id not in self.active_connections:
            return

        try:
            await self.active_connections[conversation_id].send_json({"type": "chat_message", "data": message})
            logger.debug(f"聊天消息已發送: {conversation_id}")
        except Exception as e:
            logger.error(f"發送聊天消息失敗: {e}")
            # 連接可能已斷開，移除連接
            self.disconnect(conversation_id)

    def start_heartbeat(self, conversation_id: str):
        """啟動心跳任務"""
        if conversation_id in self.heartbeat_tasks:
            # 如果已存在心跳任務，先停止它
            self.stop_heartbeat(conversation_id)

        # 創建新的心跳任務
        self.heartbeat_tasks[conversation_id] = asyncio.create_task(self._heartbeat_loop(conversation_id))
        logger.debug(f"心跳任務已啟動: {conversation_id}")

    def stop_heartbeat(self, conversation_id: str):
        """停止心跳任務"""
        if conversation_id in self.heartbeat_tasks:
            self.heartbeat_tasks[conversation_id].cancel()
            del self.heartbeat_tasks[conversation_id]
            logger.debug(f"心跳任務已停止: {conversation_id}")

    async def _heartbeat_loop(self, conversation_id: str):
        """心跳循環"""
        try:
            while conversation_id in self.active_connections:
                await self._send_heartbeat(conversation_id)
                await asyncio.sleep(25)  # 每25秒發送一次心跳
        except asyncio.CancelledError:
            logger.debug(f"心跳循環已取消: {conversation_id}")
        except Exception as e:
            logger.error(f"心跳循環發生錯誤: {e}")

    async def _send_heartbeat(self, conversation_id: str):
        """發送心跳訊息"""
        if conversation_id not in self.active_connections:
            return

        try:
            await self.active_connections[conversation_id].send_json(
                {"type": "heartbeat", "timestamp": asyncio.get_event_loop().time()}
            )
            logger.debug(f"心跳訊息已發送: {conversation_id}")
        except Exception as e:
            logger.error(f"發送心跳訊息失敗: {e}")
            # 連接可能已斷開，移除連接
            self.disconnect(conversation_id)

    async def send_stream_response(self, conversation_id: str, response: StreamChatResponse | dict[str, Any]):
        """發送流式回應"""
        if conversation_id not in self.active_connections:
            return

        try:
            websocket = self.active_connections[conversation_id]
            if isinstance(response, StreamChatResponse):
                await websocket.send_text(orjson.dumps(response.model_dump()).decode("utf-8"))
                logger.debug(f"流式回應已發送: {response.message_chunk[:20]}...")
            else:
                await websocket.send_text(orjson.dumps(response).decode("utf-8"))
                logger.debug(f"流式回應已發送: {str(response)[:20]}...")
        except Exception as e:
            logger.error(f"發送流式回應失敗: {e}")

    async def broadcast_text(self, conversation_id: str, message: str):
        """廣播文本消息"""
        if conversation_id not in self.active_connections:
            return

        try:
            await self.active_connections[conversation_id].send_text(message)
            logger.debug(f"文本消息已發送: {message[:20]}...")
        except Exception as e:
            logger.error(f"發送文本消息失敗: {e}")


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


# 創建 WebSocket 管理器實例
ws_manager = WebSocketManager()
