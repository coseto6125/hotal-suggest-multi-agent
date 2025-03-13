import argparse
import asyncio
import os

import anyio
from dotenv import load_dotenv
from loguru import logger

from config import config


async def setup_llm_provider(args):
    """設置 LLM 提供者"""
    # 命令行參數優先於配置文件
    use_ollama = args.ollama or config.llm.provider == "ollama"

    if use_ollama:
        from crewai.llms import Ollama

        # 優先使用命令行參數，其次使用配置文件
        ollama_base_url = args.ollama_url or config.llm.ollama.base_url
        ollama_model = args.ollama_model or config.llm.ollama.model

        logger.info(f"使用 Ollama API，模型: {ollama_model}，基礎 URL: {ollama_base_url}")
        return Ollama(model=ollama_model, base_url=ollama_base_url, temperature=config.llm.ollama.temperature)
    from crewai.llms import OpenAI

    # 檢查 OpenAI API 密鑰
    api_key = os.getenv("OPENAI_API_KEY") or config.llm.openai_api_key
    if not api_key:
        logger.warning("未設置 OPENAI_API_KEY 環境變數，請確保已在環境中設置或通過其他方式提供")

    logger.info(f"使用 OpenAI API，模型: {config.llm.openai_model}")
    return OpenAI(api_key=api_key, model=config.llm.openai_model, temperature=config.llm.openai_temperature)


async def main():
    """主程序入口"""
    try:
        # 載入環境變數
        load_dotenv()

        # 解析命令行參數
        parser = argparse.ArgumentParser(description="旅館推薦 Multi-Agent Chatbot 系統")
        parser.add_argument("--ollama", action="store_true", help="使用 Ollama API 而非 OpenAI")
        parser.add_argument("--ollama-url", type=str, help="Ollama API 基礎 URL")
        parser.add_argument("--ollama-model", type=str, help="Ollama 模型名稱")
        args = parser.parse_args()

        logger.info("系統啟動中...")

        # 設置 LLM 提供者
        llm = await setup_llm_provider(args)

        # TODO: 初始化 Agent 系統
        # TODO: 啟動用戶交互介面
        # TODO: 啟動系統服務

        logger.info("系統已就緒")

        # 使用 Event 替代 while 循環中的 sleep
        stop_event = anyio.Event()

        # 等待停止事件
        await stop_event.wait()

    except KeyboardInterrupt:
        logger.info("系統正在關閉...")
    except Exception as e:
        logger.exception(f"系統發生錯誤: {e!s}")
    finally:
        # TODO: 清理資源
        logger.info("系統已關閉")


if __name__ == "__main__":
    asyncio.run(main())
