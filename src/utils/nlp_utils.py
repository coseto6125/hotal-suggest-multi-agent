"""
NLP 工具模組，提供共享的自然語言處理功能
"""

import threading

import spacy
from loguru import logger

# 全局模型緩存
_spacy_models: dict[str, spacy.Language] = {}
_model_lock = threading.Lock()


def get_shared_spacy_model(model_name: str) -> spacy.Language:
    """
    獲取共享的spaCy模型，如果模型尚未載入，則載入並緩存

    Args:
        model_name: 要載入的spaCy模型名稱

    Returns:
        載入的spaCy模型
    """
    global _spacy_models

    # 檢查模型是否已經載入
    if model_name in _spacy_models:
        logger.debug(f"使用已載入的spaCy模型: {model_name}")
        return _spacy_models[model_name]

    # 使用鎖確保線程安全
    with _model_lock:
        # 再次檢查，以防在等待鎖的過程中已經被載入
        if model_name in _spacy_models:
            logger.debug(f"使用已在等待鎖過程中載入的spaCy模型: {model_name}")
            return _spacy_models[model_name]

        # 載入模型
        try:
            logger.info(f"載入spaCy模型: {model_name}")
            nlp = spacy.load(model_name)
            _spacy_models[model_name] = nlp
            logger.info(f"成功載入spaCy模型: {model_name}")
            return nlp
        except Exception as e:
            logger.error(f"載入spaCy模型失敗: {e}")
            # 如果無法載入模型，使用基本的spaCy功能
            nlp = spacy.blank("zh")
            _spacy_models[model_name] = nlp
            logger.warning(f"使用基本的spaCy功能替代模型: {model_name}")
            return nlp
