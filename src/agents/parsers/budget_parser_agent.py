"""
預算解析子Agent，專門負責解析查詢中的預算範圍
"""

import re
from typing import Any

from loguru import logger
from spacy.matcher import Matcher

from src.agents.base.base_agent import BaseAgent
from src.utils.nlp_utils import get_shared_spacy_model


class BudgetParserAgent(BaseAgent):
    """預算解析子Agent"""

    MIN_VALID_AMOUNT = 2000

    def __init__(self):
        super().__init__("BudgetParserAgent")
        self._init_regex_patterns()
        self.spacy_available = False
        try:
            self.nlp = get_shared_spacy_model("zh_core_web_md")
            self.spacy_available = True
            logger.info("成功載入spaCy中文模型")
            self._init_spacy_matcher()
        except Exception as e:
            logger.warning(f"無法載入spaCy模型: {e!s}，將使用正則表達式")
        self.err_result = {
            "error": "未提取到預算信息",
            "err_msg": " 不好意思，無法從您的訊息中得知預算範圍，方便提供一下嗎？",
        }

    def _init_regex_patterns(self):
        """初始化正則表達式模式"""
        self.currency_units = r"(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)?"
        self.time_units = r"(?:/晚|每晚|一晚)?"
        num_pattern = r"(\d+(?:,\d+)?(?:\.\d+)?)"
        self.patterns = {
            "range": re.compile(
                rf"{num_pattern}\s*(?:-|~|到)\s*{num_pattern}\s*{self.currency_units}{self.time_units}"
            ),
            "limit": re.compile(
                rf"(?:最低|至少|起碼|最高|最多|不超過)\s*{num_pattern}\s*{self.currency_units}{self.time_units}"
            ),
            "approx": re.compile(rf"{num_pattern}\s*{self.currency_units}{self.time_units}\s*(?:左右|上下|附近|大約)"),
            "any": re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:萬|k|K|千|元|塊|NTD|TWD|台幣|新台幣)?"),
        }

    def _init_spacy_matcher(self):
        """初始化spaCy匹配器"""
        if not self.spacy_available:
            return
        self.matcher = Matcher(self.nlp.vocab)
        self.matcher.add(
            "PRICE",
            [
                [{"LIKE_NUM": True}, {"TEXT": {"IN": ["-", "~", "到"]}}, {"LIKE_NUM": True}],
                [{"TEXT": {"IN": ["最低", "至少", "起碼", "最高", "最多", "不超過"]}}, {"LIKE_NUM": True}],
                [
                    {"LIKE_NUM": True},
                    {"OP": "?", "TEXT": {"IN": ["元", "塊", "NT$", "台幣"]}},
                    {"OP": "?", "TEXT": {"IN": ["左右", "上下", "附近"]}},
                ],
            ],
        )

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理預算解析請求"""
        logger.debug(f"[{self.name}] 處理請求")
        query = state.get("query", "")
        if "無預算" in query:
            return {"lowest_price": None, "highest_price": None}
        try:
            budget = self._parse_with_regex(query)
            if not budget.get("lowest_price") and not budget.get("highest_price") and self.spacy_available:
                budget = self._parse_with_spacy(query)
            if not budget.get("lowest_price") and not budget.get("highest_price"):
                logger.info(f"[{self.name}] 未提取到預算: {query}")
                return self.err_result
            self._validate_budget(budget)
            if not self._is_valid_budget(budget):
                logger.warning(f"[{self.name}] 預算過低: {budget}")
                return self.err_result
            logger.info(f"[{self.name}] 成功提取預算: {budget}")
            return budget
        except Exception as e:
            logger.error(f"[{self.name}] 解析失敗: {e}")
            return self.err_result

    def _parse_amount(self, text: str, query: str) -> int | None:
        """解析金額並調整單位，低於MIN_VALID_AMOUNT返回None"""
        amount = float(text.replace(",", ""))
        if "萬" in query:
            amount *= 10000
        elif "k" in query.lower() or "千" in query:
            amount *= 1000
        amount = int(amount)
        return amount if amount >= self.MIN_VALID_AMOUNT else None

    def _parse_with_regex(self, query: str) -> dict[str, Any]:
        """使用正則表達式解析預算"""
        budget = {}

        # 範圍模式
        if match := self.patterns["range"].search(query):
            min_amount = self._parse_amount(match.group(1), query)
            max_amount = self._parse_amount(match.group(2), query)
            if min_amount and max_amount:
                budget = {"lowest_price": min_amount, "highest_price": max_amount}
                return budget

        # 極限模式（最低/最高）
        if match := self.patterns["limit"].search(query):
            amount = self._parse_amount(match.group(1), query)
            if amount:
                if any(kw in match.group(0) for kw in ["最低", "至少", "起碼"]):
                    budget = {"lowest_price": amount, "highest_price": amount * 2}
                elif any(kw in match.group(0) for kw in ["最高", "最多", "不超過"]):
                    budget = {"lowest_price": 0, "highest_price": amount}
                if budget:
                    return budget

        # 大約模式
        if match := self.patterns["approx"].search(query):
            amount = self._parse_amount(match.group(1), query)
            if amount:
                buffer = int(amount * 0.2)
                budget = {"lowest_price": amount - buffer, "highest_price": amount + buffer}
                return budget

        # 後備方案
        if match := self.patterns["any"].search(query):
            amount = self._parse_amount(match.group(1), query)
            if amount:
                buffer = int(amount * 0.2)
                if any(kw in query for kw in ["最多", "不超過", "最高"]):
                    budget = {"lowest_price": 0, "highest_price": amount}
                else:
                    budget = {"lowest_price": amount - buffer, "highest_price": amount + buffer}
                return budget

        return budget

    def _parse_with_spacy(self, query: str) -> dict[str, Any]:
        """使用spaCy解析預算"""
        budget = {}
        doc = self.nlp(query)
        matches = self.matcher(doc)

        for _, start, end in matches:
            span = doc[start:end]
            nums = [t.text for t in span if t.like_num]
            if not nums:
                continue

            if ("-" in span.text or "~" in span.text or "到" in span.text) and len(nums) >= 2:
                min_amount = self._parse_amount(nums[0], query)
                max_amount = self._parse_amount(nums[1], query)
                if min_amount and max_amount:
                    return {"lowest_price": min_amount, "highest_price": max_amount}
                continue

            amount = self._parse_amount(nums[0], query)
            if not amount:
                continue

            if any(kw in span.text for kw in ["最低", "至少", "起碼"]):
                return {"lowest_price": amount, "highest_price": amount * 2}
            if any(kw in span.text for kw in ["最高", "最多", "不超過"]):
                return {"lowest_price": 0, "highest_price": amount}

            buffer = int(amount * 0.2)
            return {"lowest_price": amount - buffer, "highest_price": amount + buffer}

        for ent in doc.ents:
            if ent.label_ in {"MONEY", "CARDINAL"} and any(unit in query for unit in ["元", "塊", "NT$", "台幣"]):
                if amount_text := re.search(r"\d+(?:,\d+)?", ent.text):
                    amount = self._parse_amount(amount_text.group(), query)
                    if amount:
                        buffer = int(amount * 0.2)
                        if any(kw in query for kw in ["最多", "不超過", "最高"]):
                            return {"lowest_price": 0, "highest_price": amount}
                        return {"lowest_price": amount - buffer, "highest_price": amount + buffer}

        return budget

    def _is_valid_budget(self, budget: dict[str, Any]) -> bool:
        """檢查預算是否有效"""
        lowest = budget.get("lowest_price")
        highest = budget.get("highest_price")
        return (highest is not None and highest >= self.MIN_VALID_AMOUNT) or (
            lowest is not None and lowest >= self.MIN_VALID_AMOUNT
        )

    def _validate_budget(self, budget: dict[str, Any]) -> None:
        """驗證並調整預算範圍"""
        lowest = budget.get("lowest_price")
        highest = budget.get("highest_price")
        if lowest is not None and highest is not None and lowest > highest:
            budget["lowest_price"], budget["highest_price"] = highest, lowest
