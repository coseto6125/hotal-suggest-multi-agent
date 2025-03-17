"""
配置模組，用於加載和管理系統配置
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

# 使用模組級別變數來追蹤是否已經初始化
_config_initialized = False
_config_instance = None


class APIConfig(BaseModel):
    """API 配置"""

    base_url: str = os.getenv(
        "API_BASE_URL", "https://k6oayrgulgb5sasvwj3tsy7l7u0tikfd.lambda-url.ap-northeast-1.on.aws"
    )
    api_key: str = os.getenv("API_KEY", "DhDkXZkGXaYBZhkk1Z9m9BuZDJGy")
    timeout: int = int(os.getenv("API_TIMEOUT", "30"))


class LLMConfig(BaseModel):
    """LLM 配置"""

    provider: str = os.getenv("LLM_PROVIDER", "ollama")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY", "example_api_key")


class OllamaConfig(BaseModel):
    """Ollama 配置"""

    enabled: bool = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))


class DucklingConfig(BaseModel):
    """Duckling 配置"""

    enabled: bool = os.getenv("DUCKLING_ENABLED", "true").lower() == "true"
    base_url: str = os.getenv("DUCKLING_BASE_URL", "http://localhost:6579")
    locale: str = os.getenv("DUCKLING_LOCALE", "zh_TW")
    timeout: int = int(os.getenv("DUCKLING_TIMEOUT", "30"))


class SystemConfig(BaseModel):
    """系統配置"""

    initial_response_timeout: int = int(os.getenv("INITIAL_RESPONSE_TIMEOUT", "5"))
    complete_response_timeout: int = int(os.getenv("COMPLETE_RESPONSE_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


class FastAPIConfig(BaseModel):
    """FastAPI 配置"""

    host: str = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port: int = int(os.getenv("FASTAPI_PORT", "8000"))
    reload: bool = os.getenv("FASTAPI_RELOAD", "true").lower() == "true"


class Config(BaseModel):
    """總配置"""

    api: APIConfig = APIConfig()
    llm: LLMConfig = LLMConfig()
    ollama: OllamaConfig = OllamaConfig()
    duckling: DucklingConfig = DucklingConfig()
    system: SystemConfig = SystemConfig()
    fastapi: FastAPIConfig = FastAPIConfig()


def initialize_config():
    """初始化配置，確保只執行一次"""
    global _config_initialized, _config_instance

    if _config_initialized:
        return _config_instance
    # 加載環境變數
    load_dotenv()
    # 創建配置實例
    _config_instance = Config()

    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)

    # 配置日誌
    logger.add(
        "logs/app.log", level=_config_instance.system.log_level, rotation="10 MB", retention="1 week", serialize=True
    )

    # 輸出配置信息
    logger.info(f"加載配置: {_config_instance.model_dump_json(indent=2)}")

    _config_initialized = True
    return _config_instance


# 創建配置實例
config = initialize_config()


def get_config():
    """獲取配置實例"""
    global config
    return config
