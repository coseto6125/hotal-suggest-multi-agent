"""
WebSocket 管理器模組

負責管理 WebSocket 連接和消息廣播。
"""

from typing import Any

from fastapi import WebSocket
from loguru import logger


class WebSocketManager:
    """WebSocket 管理器類別"""

    def __init__(self):
        """初始化 WebSocket 管理器"""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        """接受 WebSocket 連接"""
        await websocket.accept()
        self.active_connections[conversation_id] = websocket
        logger.info(f"WebSocket 連接已建立: {conversation_id}")

    def disconnect(self, conversation_id: str):
        """關閉 WebSocket 連接"""
        if conversation_id in self.active_connections:
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

    async def broadcast_chat_message(self, conversation_id: str, message: dict[str, Any]):
        """廣播聊天消息"""
        if conversation_id not in self.active_connections:
            return

        try:
            await self.active_connections[conversation_id].send_json({"type": "chat_message", "data": message})
            logger.debug(f"聊天消息已發送: {conversation_id}")
        except Exception as e:
            logger.error(f"發送聊天消息失敗: {e}")


# 創建 WebSocket 管理器實例
ws_manager = WebSocketManager()
