"""
人數解析子Agent，專門負責解析查詢中的人數信息
"""

import re
from typing import Any, ClassVar

import spacy
from loguru import logger
from spacy.matcher import Matcher

from src.agents.base.base_agent import BaseAgent
from src.utils.nlp_utils import get_shared_spacy_model


class GuestParserAgent(BaseAgent):
    """人數解析子Agent"""

    _shared_nlp: ClassVar[spacy.Language | None] = None
    MAX_GUESTS = 10

    def __init__(self):
        super().__init__("GuestParserAgent")
        self._init_regex_patterns()
        self.spacy_available = False
        try:
            self.nlp = get_shared_spacy_model("zh_core_web_md")
            self.spacy_available = True
            logger.info("成功載入spaCy中文模型")
            self._init_spacy_matcher()
        except Exception as e:
            logger.warning(f"無法載入spaCy模型: {e!s}，將使用正則表達式")
        self.chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "兩": 2, "两": 2}

    def _init_regex_patterns(self):
        """初始化正則表達式模式"""
        unit = r"(?:個|位|名)?"
        adult = r"(?:大人|成人|大)"
        child = r"(?:小孩|兒童|孩子|小|嬰兒)"
        conn = r"(?:，|,|、|。|\s)"
        num = r"(\d+|[一二三四五六七八九十兩两])"
        self.patterns = {
            "direct": re.compile(rf"(?:{adult}\s*)?{num}\s*{unit}{adult}\s*{num}\s*{unit}{child}|{num}\s*大\s*{num}\s*小"),
            "total": re.compile(rf"(?:一共|總共|共|全家)?\s*{num}\s*{unit}(?:人|位){conn}(?:其中|包括|含|包含)?\s*{num}\s*{unit}{child}"),
            "family": re.compile(rf"(?:一家|全家|我們是)?{num}口(?:之)?(?:家|家庭)?"),
            "special": re.compile(r"夫妻|兩口子|夫婦|伴侶|情侶|一對|我(?:和|與|跟)(?:太太|老婆|妻子|先生|老公|丈夫)|父母|爸媽|爸爸媽媽|家長|(?:祖父母|爺爺奶奶|外公外婆)"),
        }

    def _init_spacy_matcher(self):
        """初始化spaCy匹配器"""
        self.matcher = Matcher(self.nlp.vocab)
        self.matcher.add("GUEST_COUNT", [
            [{"LIKE_NUM": True}, {"TEXT": {"IN": ["大", "大人", "成人"]}}, {"LIKE_NUM": True}, {"TEXT": {"IN": ["小", "小孩", "兒童", "孩子"]}}],
            [{"LIKE_NUM": True}, {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}}, {"TEXT": {"IN": ["人", "位"]}}],
        ])

    def _parse_number(self, text: str) -> int | None:
        """解析數字，超過MAX_GUESTS返回None"""
        num = self.chinese_nums.get(text, int(text)) if text.isdigit() or text in self.chinese_nums else None
        return num if num and num <= self.MAX_GUESTS else None

    def parse(self, query: str) -> dict[str, int]:
        """解析查詢中的人數信息"""
        guests = self._parse_with_regex(query)
        if guests["adults"] is not None or guests["children"] is not None:
            return guests
        return self._parse_with_spacy(query) if self.spacy_available else guests

    def _parse_with_regex(self, query: str) -> dict[str, int]:
        """使用正則表達式解析人數信息"""
        guests = {"adults": None, "children": None}

        # 直接模式
        if match := self.patterns["direct"].search(query):
            adults, children = self._parse_number(match.group(1)), self._parse_number(match.group(2))
            if adults and children:
                guests["adults"], guests["children"] = adults, children
                logger.debug(f"直接模式: 成人={adults}, 兒童={children}")
                return guests

        # 總數模式
        if match := self.patterns["total"].search(query):
            total, children = self._parse_number(match.group(1)), self._parse_number(match.group(2))
            if total and children:
                adults = max(1, total - children)
                if adults <= self.MAX_GUESTS:
                    guests["adults"], guests["children"] = adults, children
                    logger.debug(f"總數模式: 總數={total}, 成人={adults}, 兒童={children}")
                    return guests

        # 家庭模式
        if match := self.patterns["family"].search(query):
            total = self._parse_number(match.group(1))
            if total:
                guests["adults"], guests["children"] = 2, max(0, total - 2)
                logger.debug(f"家庭模式: 總數={total}, 成人=2, 兒童={guests['children']}")
                return guests

        # 特殊模式
        if match := self.patterns["special"].search(query):
            text = match.group(0)
            guests["adults"] = 2
            if "祖父母" in text or "爺爺奶奶" in text or "外公外婆" in text:
                guests["adults"] += 2
            logger.debug(f"特殊模式: 成人={guests['adults']}")
            return guests

        return guests

    def _parse_with_spacy(self, query: str) -> dict[str, int]:
        """使用spaCy解析人數信息"""
        guests = {"adults": None, "children": None}
        doc = self.nlp(query)
        matches = self.matcher(doc)

        for _, start, end in matches:
            span = doc[start:end]
            nums = [self._parse_number(t.text) for t in span if t.like_num]
            text = span.text
            if "大" in text and len(nums) >= 2:
                guests["adults"], guests["children"] = nums[0], nums[1]
            elif "人" in text or "位" in text and nums:
                total = nums[0]
                guests["adults"] = total
                guests["children"] = 0

        if guests["adults"] is None and "大" in query and "小" in query:
            tokens = [t.text for t in doc]
            for i, t in enumerate(tokens):
                if t == "大" and i > 0 and i < len(tokens) - 2 and tokens[i + 2] == "小":
                    adults = self._parse_number(tokens[i - 1])
                    children = self._parse_number(tokens[i + 1])
                    if adults and children:
                        guests["adults"], guests["children"] = adults, children
                        break

        if guests["adults"] or guests["children"]:
            logger.debug(f"spaCy解析: 成人={guests['adults']}, 兒童={guests['children']}")
        return guests

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理客人信息解析請求"""
        logger.debug(f"[{self.name}] 處理請求")
        query = state.get("query", "")
        try:
            guests = self.parse(query)
            if guests["adults"] is None:
                return {"error": "人數解析失敗", "err_msg": "  抱歉，無法辨識人數訊息，可用'2大1小'表達。"}
            return guests
        except Exception as e:
            logger.error(f"[{self.name}] 解析失敗: {e}")
            return {"error": f"解析失敗（{e!s}）", "err_msg": "  抱歉，無法辨識人數訊息，可用'2大1小'表達。"}