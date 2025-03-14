"""
主入口文件，用於啟動FastAPI應用
"""

import uvicorn
from loguru import logger

from src.config import config

if __name__ == "__main__":
    logger.info(f"啟動旅館推薦系統，監聽地址: {config.fastapi.host}:{config.fastapi.port}")
    uvicorn.run("src.web.app:app", host=config.fastapi.host, port=config.fastapi.port, reload=config.fastapi.reload)
