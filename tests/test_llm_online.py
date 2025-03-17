"""
測試 LLM 服務
"""

import os

import pytest
from dotenv import load_dotenv

from src.config import logger

# 強制重新加載環境變數
load_dotenv(override=True)

# 輸出環境變數
logger.info(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
logger.info(f"OLLAMA_ENABLED: {os.getenv('OLLAMA_ENABLED')}")
logger.info(f"OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL')}")

# 導入 llm_service 實例
try:
    logger.info("開始導入 llm_service 實例")

    logger.info("成功導入 llm_service 實例")
except Exception as e:
    logger.error(f"導入 llm_service 實例失敗: {e!s}")
    raise


# 測試 llm_service
@pytest.mark.asyncio
async def test_llm():
    logger.info("開始測試 LLM 服務")
    try:
        response = await llm_service.generate_response([{"role": "user", "content": "你好，請用一句話介紹一下自己"}])
        logger.info(f"LLM 回應: {response}")
    except Exception as e:
        logger.error(f"LLM 服務測試失敗: {e!s}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_llm())
