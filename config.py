import os

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, Field

# 載入環境變數
load_dotenv()


class APIConfig(BaseModel):
    """API 配置"""

    base_url: str = os.getenv("API_BASE_URL", "https://raccoonai-agents-api.readme.io")
    api_key: str = os.getenv("API_KEY", "DhDkXZkGXaYBZhkk1Z9m9BuZDJGy")  # cspell:disable-line
    timeout: int = int(os.getenv("API_TIMEOUT", "30"))


class OllamaConfig(BaseModel):
    """Ollama 配置"""

    enabled: bool = os.getenv("OLLAMA_ENABLED", "false").lower() in ("true", "1", "yes")
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3")
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))


class LLMConfig(BaseModel):
    """LLM 配置"""

    provider: str = os.getenv("LLM_PROVIDER", "openai")  # 'openai' 或 'ollama'
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)


class SystemConfig(BaseModel):
    """系統配置"""

    initial_response_timeout: int = int(os.getenv("INITIAL_RESPONSE_TIMEOUT", "5"))
    complete_response_timeout: int = int(os.getenv("COMPLETE_RESPONSE_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


class Config:
    """全局配置"""

    api: APIConfig = Field(default_factory=APIConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)


# 設定全局日誌等級
logger.configure(handlers=[{"sink": lambda msg: print(msg), "level": SystemConfig().log_level}])

config = Config()
