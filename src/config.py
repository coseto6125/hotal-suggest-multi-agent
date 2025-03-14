"""
配置模組，用於加載和管理系統配置
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

# 加載環境變數
load_dotenv()


class APIConfig(BaseModel):
    """API 配置"""

    base_url: str = os.getenv("API_BASE_URL", "https://raccoonai-agents-api.readme.io")
    api_key: str = os.getenv("API_KEY", "")
    timeout: int = int(os.getenv("API_TIMEOUT", "30"))


class LLMConfig(BaseModel):
    """LLM 配置"""

    provider: str = os.getenv("LLM_PROVIDER", "openai")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY", "")


class OllamaConfig(BaseModel):
    """Ollama 配置"""

    enabled: bool = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3")
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))


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
    system: SystemConfig = SystemConfig()
    fastapi: FastAPIConfig = FastAPIConfig()


# 創建配置實例
config = Config()

# 配置日誌
logger.add("logs/app.log", level=config.system.log_level, rotation="10 MB", retention="1 week", serialize=True)

# 確保日誌目錄存在
Path("logs").mkdir(exist_ok=True)

# 輸出配置信息
logger.info(f"加載配置: {config.model_dump_json(indent=2)}")
