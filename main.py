"""
主入口文件，用於啟動FastAPI應用
"""

import logging
import os

import uvicorn
from loguru import logger

from src.config import config


class InterceptHandler(logging.Handler):
    """
    將標準庫的 logging 重定向到 loguru 的處理程序
    """

    def emit(self, record):
        # 獲取對應的 loguru 級別
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 尋找調用者
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """
    設置日誌配置，將 uvicorn 的日誌重定向到 loguru
    """
    # 移除所有默認處理程序
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(config.system.log_level)

    # 移除每個 uvicorn 日誌的默認處理程序
    for name in logging.root.manager.loggerDict:
        if name.startswith("uvicorn."):
            logging_logger = logging.getLogger(name)
            logging_logger.handlers = [InterceptHandler()]
            logging_logger.propagate = False

    # 設置 uvicorn 的 access 日誌
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = [InterceptHandler()]
    access_logger.propagate = False

    # 設置 uvicorn 的 error 日誌
    error_logger = logging.getLogger("uvicorn.error")
    error_logger.handlers = [InterceptHandler()]
    error_logger.propagate = False


# 在模組級別設置日誌，確保在 reload 模式下也能正確工作
setup_logging()

if __name__ == "__main__":
    logger.info(f"啟動旅館推薦系統，監聽地址: {config.fastapi.host}:{config.fastapi.port}")

    # 設置環境變數，確保在 reload 模式下子進程也使用相同的日誌配置
    os.environ["PYTHONUNBUFFERED"] = "1"

    uvicorn.run(
        "src.web.app:app",
        host=config.fastapi.host,
        port=config.fastapi.port,
        reload=config.fastapi.reload,
        log_config=None,  # 禁用 uvicorn 的默認日誌配置
    )
