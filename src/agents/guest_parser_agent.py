"""
人數解析子Agent，專門負責解析查詢中的人數信息
"""

import re
from typing import Any

import spacy
from loguru import logger
from spacy.matcher import Matcher

from src.agents.base_sub_agent import BaseSubAgent
from src.services.llm_service import llm_service


class GuestParserAgent(BaseSubAgent):
    """人數解析子Agent"""

    def __init__(self):
        """初始化人數解析子Agent"""
        super().__init__("GuestParserAgent")
        # 人數正則表達式模式
        self.adult_patterns = [
            re.compile(r"(\d+)\s*(?:個|位|名)?(?:大人|成人|大)"),
            re.compile(r"(?:大人|成人|大)\s*(\d+)\s*(?:個|位|名)?"),
        ]
        self.child_patterns = [
            re.compile(r"(\d+)\s*(?:個|位|名)?(?:小孩|兒童|孩子|小|嬰兒)"),
            re.compile(r"(?:小孩|兒童|孩子|小|嬰兒)\s*(\d+)\s*(?:個|位|名)?"),
        ]
        self.total_patterns = [
            re.compile(r"(\d+)\s*(?:個|位|名)?(?:人|位)"),
            re.compile(r"(?:一共|總共|共|全家)\s*(\d+)\s*(?:個|位|名)?(?:人|位|口)"),
        ]

        # 家庭人數相關模式
        self.family_size_patterns = [
            re.compile(r"一家(\d+)口"),
            re.compile(r"(\d+)口(?:之)?家"),
            re.compile(r"(\d+)口家庭"),
            re.compile(r"家庭(\d+)口"),
            re.compile(r"我們是(\d+)口(?:之)?家"),
            re.compile(r"我們是(\d+)口家庭"),
            re.compile(r"(\d+)人家庭"),
            re.compile(r"家庭(\d+)人"),
            re.compile(r"全家(\d+)口"),
        ]

        # 特殊家庭成員模式
        self.couple_patterns = [
            re.compile(r"夫妻|兩口子|夫婦|伴侶|情侶|一對"),
            re.compile(r"我(?:和|與|跟)(?:太太|老婆|妻子|先生|老公|丈夫)"),
        ]

        self.grandparents_patterns = [
            re.compile(r"(?:祖父母|爺爺奶奶|外公外婆)"),
        ]

        self.parents_patterns = [
            re.compile(r"父母|爸媽|爸爸媽媽|家長"),
        ]

        # 初始化spaCy模型
        self.spacy_available = False
        try:
            self.nlp = spacy.load("zh_core_web_sm")
            self.spacy_available = True
            logger.info("成功載入spaCy中文模型")

            # 設置spaCy匹配器
            self.matcher = Matcher(self.nlp.vocab)

            # 添加成人數量匹配模式
            self.matcher.add(
                "ADULT_COUNT",
                [
                    [
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                        {"TEXT": {"IN": ["大人", "成人", "大"]}},
                    ],
                    [
                        {"TEXT": {"IN": ["大人", "成人", "大"]}},
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                    ],
                    [
                        {"TEXT": {"IN": ["大人", "成人", "大"]}},
                        {"OP": "?", "TEXT": {"IN": ["有", "是"]}},
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                    ],
                ],
            )

            # 添加兒童數量匹配模式
            self.matcher.add(
                "CHILD_COUNT",
                [
                    [
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                        {"TEXT": {"IN": ["小孩", "兒童", "孩子", "小"]}},
                    ],
                    [
                        {"TEXT": {"IN": ["小孩", "兒童", "孩子", "小"]}},
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                    ],
                    [
                        {"TEXT": {"IN": ["小孩", "兒童", "孩子", "小"]}},
                        {"OP": "?", "TEXT": {"IN": ["有", "是"]}},
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                    ],
                ],
            )

            # 添加總人數匹配模式
            self.matcher.add(
                "TOTAL_COUNT",
                [
                    [
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                        {"TEXT": {"IN": ["人", "位"]}},
                    ],
                    [
                        {"TEXT": {"IN": ["一共", "總共", "共"]}},
                        {"LIKE_NUM": True},
                        {"OP": "?", "TEXT": {"IN": ["個", "位", "名"]}},
                        {"OP": "?", "TEXT": {"IN": ["人", "位"]}},
                    ],
                    [
                        {"TEXT": {"IN": ["一家", "家裡", "家人"]}},
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["口", "人"]}},
                    ],
                ],
            )

            # 添加家庭成員匹配模式
            self.matcher.add(
                "FAMILY_MEMBERS",
                [
                    [{"TEXT": {"IN": ["夫妻", "兩口子", "夫婦", "伴侶", "情侶"]}}],
                    [{"TEXT": {"IN": ["一對", "一雙"]}}, {"TEXT": {"IN": ["夫妻", "夫婦", "伴侶", "情侶"]}}],
                    [
                        {"TEXT": {"IN": ["我", "我們"]}},
                        {"TEXT": {"IN": ["和", "與", "跟"]}},
                        {"TEXT": {"IN": ["太太", "老婆", "妻子", "先生", "老公", "丈夫"]}},
                    ],
                    [{"TEXT": {"IN": ["父母", "爸媽", "爸爸媽媽", "家長"]}}],
                ],
            )

            # 添加家庭人數匹配模式
            self.matcher.add(
                "FAMILY_SIZE",
                [
                    [{"TEXT": {"IN": ["一家", "家庭"]}}, {"LIKE_NUM": True}, {"TEXT": {"IN": ["口", "人"]}}],
                    [{"LIKE_NUM": True}, {"TEXT": {"IN": ["口", "人"]}}, {"TEXT": {"IN": ["家", "家庭"]}}],
                    [
                        {"TEXT": {"IN": ["我們", "我"]}},
                        {"TEXT": {"IN": ["是"]}},
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["口", "人"]}},
                        {"OP": "?", "TEXT": {"IN": ["家", "家庭"]}},
                    ],
                ],
            )

        except Exception as e:
            logger.warning(f"無法載入spaCy中文模型: {e!s}，將使用正則表達式和LLM解析")
            self.spacy_available = False

    def parse(self, query: str) -> dict[str, int]:
        """
        解析查詢中的人數信息，返回成人和兒童數量

        Args:
            query: 用戶查詢字符串

        Returns:
            包含成人和兒童數量的字典 {"adults": int, "children": int}
        """
        # 使用同步方式處理查詢
        guests = {"adults": None, "children": None}

        # 首先檢查是否有家庭人數表達式
        family_size = self._extract_family_size(query)
        if family_size is not None:
            # 假設家庭中有2位成人
            guests["adults"] = 2
            # 剩餘的是兒童
            guests["children"] = max(0, family_size - 2)
            logger.debug(
                f"從家庭人數表達式推斷: 總人數={family_size}, 成人={guests['adults']}, 兒童={guests['children']}"
            )

        # 檢查是否有特殊家庭成員表達
        additional_adults = self._extract_additional_adults(query)
        if additional_adults > 0:
            if guests["adults"] is not None:
                guests["adults"] += additional_adults
            else:
                guests["adults"] = additional_adults
            logger.debug(f"從特殊家庭成員表達推斷額外成人: {additional_adults}")

        # 檢查是否有額外的兒童
        additional_children = self._extract_additional_children(query)
        if additional_children > 0:
            if guests["children"] is not None:
                guests["children"] += additional_children
            else:
                guests["children"] = additional_children
            logger.debug(f"從查詢中提取到額外兒童: {additional_children}")

        # 如果沒有找到家庭人數表達式，或者只找到了部分信息，繼續使用其他方法
        if self.spacy_available and (guests["adults"] is None or guests["children"] is None):
            spacy_guests = self._extract_guests_with_spacy(query)

            # 只更新尚未確定的值
            if guests["adults"] is None:
                guests["adults"] = spacy_guests["adults"]
            if guests["children"] is None:
                guests["children"] = spacy_guests["children"]

            if guests["adults"] is not None or guests["children"] is not None:
                logger.debug(f"使用spaCy解析到人數: 成人={guests['adults']}, 兒童={guests['children']}")

        # 如果spaCy無法解析或不可用，嘗試使用正則表達式解析
        if guests["adults"] is None or guests["children"] is None:
            regex_guests = self._extract_guests_with_regex(query)

            # 只更新尚未確定的值
            if guests["adults"] is None:
                guests["adults"] = regex_guests["adults"]
            if guests["children"] is None:
                guests["children"] = regex_guests["children"]

            if guests["adults"] is not None or guests["children"] is not None:
                logger.debug(f"使用正則表達式解析到人數: 成人={guests['adults']}, 兒童={guests['children']}")

        # 如果仍然無法解析，設置默認值
        if guests["adults"] is None:
            guests["adults"] = 2  # 默認2位成人
            logger.info("無法解析成人數量，使用默認值: 2")

        if guests["children"] is None:
            guests["children"] = 0  # 默認0位兒童
            logger.info("無法解析兒童數量，使用默認值: 0")

        return guests

    def _extract_family_size(self, query: str) -> int | None:
        """從查詢中提取家庭人數"""
        # 檢查"全家X口"表達式
        whole_family_pattern = re.compile(r"(?:全家|我們全家)([一二三四五六七八九十\d]+)(?:口|人)")
        match = whole_family_pattern.search(query)
        if match:
            try:
                # 處理中文數字
                size_text = match.group(1)
                if size_text in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]:
                    chinese_nums = {
                        "一": 1,
                        "二": 2,
                        "三": 3,
                        "四": 4,
                        "五": 5,
                        "六": 6,
                        "七": 7,
                        "八": 8,
                        "九": 9,
                        "十": 10,
                    }
                    family_size = chinese_nums[size_text]
                else:
                    family_size = int(size_text)
                logger.debug(f"從'全家X口'表達式提取到家庭人數: {family_size}")
                return family_size
            except (ValueError, IndexError):
                pass

        # 檢查"一家X口"表達式
        family_pattern = re.compile(r"(?:一家|家庭|我們一家|我們家庭)([一二三四五六七八九十\d]+)口")
        match = family_pattern.search(query)
        if match:
            try:
                # 處理中文數字
                size_text = match.group(1)
                if size_text in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]:
                    chinese_nums = {
                        "一": 1,
                        "二": 2,
                        "三": 3,
                        "四": 4,
                        "五": 5,
                        "六": 6,
                        "七": 7,
                        "八": 8,
                        "九": 9,
                        "十": 10,
                    }
                    family_size = chinese_nums[size_text]
                else:
                    family_size = int(size_text)
                logger.debug(f"從'一家X口'表達式提取到家庭人數: {family_size}")
                return family_size
            except (ValueError, IndexError):
                pass

        # 檢查各種家庭人數表達式
        for pattern in self.family_size_patterns:
            match = pattern.search(query)
            if match:
                try:
                    family_size = int(match.group(1))
                    logger.debug(f"從查詢中提取到家庭人數: {family_size}")
                    return family_size
                except (ValueError, IndexError):
                    continue

        # 檢查特殊表達，如"三口之家"（中文數字）
        chinese_num_pattern = re.compile(r"[一二三四五六七八九十]口(?:之)?家")
        match = chinese_num_pattern.search(query)
        if match:
            text = match.group(0)[0]
            chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            if text in chinese_nums:
                family_size = chinese_nums[text]
                logger.debug(f"從查詢中提取到家庭人數(中文數字): {family_size}")
                return family_size

        return None

    def _extract_additional_adults(self, query: str) -> int:
        """從查詢中提取額外的成人數量（如祖父母、父母等）"""
        additional_adults = 0

        # 檢查是否有祖父母
        for pattern in self.grandparents_patterns:
            if pattern.search(query):
                additional_adults += 2
                logger.debug("查詢中包含祖父母，添加2位成人")
                break

        # 檢查是否有父母（如果不是主要家庭成員）
        if not any(p.search(query) for p in self.family_size_patterns):
            for pattern in self.parents_patterns:
                if pattern.search(query):
                    additional_adults += 2
                    logger.debug("查詢中包含父母，添加2位成人")
                    break

        # 檢查是否有夫妻（如果不是主要家庭成員）
        if not any(p.search(query) for p in self.family_size_patterns):
            for pattern in self.couple_patterns:
                if pattern.search(query):
                    additional_adults += 2
                    logger.debug("查詢中包含夫妻，添加2位成人")
                    break

        return additional_adults

    def _extract_additional_children(self, query: str) -> int:
        """從查詢中提取額外的兒童數量"""
        additional_children = 0

        # 檢查是否有"還有X個小孩/嬰兒"等表達
        extra_child_pattern = re.compile(r"還有(\d+|[一二三四五六七八九十])(?:個|位|名)?(?:小孩|兒童|孩子|小|嬰兒)")
        match = extra_child_pattern.search(query)
        if match:
            try:
                # 處理中文數字
                count_text = match.group(1)
                if count_text in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]:
                    chinese_nums = {
                        "一": 1,
                        "二": 2,
                        "三": 3,
                        "四": 4,
                        "五": 5,
                        "六": 6,
                        "七": 7,
                        "八": 8,
                        "九": 9,
                        "十": 10,
                    }
                    additional_children = chinese_nums[count_text]
                else:
                    additional_children = int(count_text)
                logger.debug(f"從'還有X個小孩'表達式提取到額外兒童: {additional_children}")
            except (ValueError, IndexError):
                pass

        return additional_children

    def _extract_guests_with_spacy(self, query: str) -> dict[str, int | None]:
        """使用spaCy從查詢中提取人數"""
        if not self.spacy_available:
            return {"adults": None, "children": None}

        guests = {"adults": None, "children": None}
        family_info = {"has_couple": False, "has_parents": False}

        # 解析文本
        doc = self.nlp(query)

        # 使用匹配器查找匹配項
        matches = self.matcher(doc)

        # 處理匹配結果
        for match_id, start, end in matches:
            match_text = doc[start:end].text
            match_type = self.nlp.vocab.strings[match_id]

            logger.debug(f"spaCy匹配: {match_type} - {match_text}")

            if match_type == "ADULT_COUNT":
                # 提取成人數量
                adults = self._extract_number_from_span(doc[start:end])
                if adults is not None and (guests["adults"] is None or adults > guests["adults"]):
                    guests["adults"] = adults

            elif match_type == "CHILD_COUNT":
                # 提取兒童數量
                children = self._extract_number_from_span(doc[start:end])
                if children is not None and (guests["children"] is None or children > guests["children"]):
                    guests["children"] = children

            elif match_type == "TOTAL_COUNT":
                # 提取總人數
                total = self._extract_number_from_span(doc[start:end])
                if total is not None:
                    # 如果已經有兒童數量，推斷成人數量
                    if guests["children"] is not None and guests["adults"] is None:
                        guests["adults"] = max(1, total - guests["children"])
                    # 如果已經有成人數量，推斷兒童數量
                    elif guests["adults"] is not None and guests["children"] is None:
                        guests["children"] = max(0, total - guests["adults"])
                    # 如果都沒有，假設全部是成人
                    elif guests["adults"] is None and guests["children"] is None:
                        guests["adults"] = total
                        guests["children"] = 0

            elif match_type == "FAMILY_MEMBERS":
                # 識別家庭成員信息
                if any(
                    term in match_text
                    for term in [
                        "夫妻",
                        "兩口子",
                        "夫婦",
                        "伴侶",
                        "情侶",
                        "太太",
                        "老婆",
                        "妻子",
                        "先生",
                        "老公",
                        "丈夫",
                    ]
                ):
                    family_info["has_couple"] = True
                if any(term in match_text for term in ["父母", "爸媽", "爸爸媽媽", "家長"]):
                    family_info["has_parents"] = True

            elif match_type == "FAMILY_SIZE":
                # 提取家庭人數
                total = self._extract_number_from_span(doc[start:end])
                if total is not None:
                    # 假設家庭中有2位成人
                    if guests["adults"] is None:
                        guests["adults"] = 2
                    # 剩餘的是兒童
                    if guests["children"] is None:
                        guests["children"] = max(0, total - guests["adults"])
                    logger.debug(
                        f"從家庭人數表達式推斷: 總人數={total}, 成人={guests['adults']}, 兒童={guests['children']}"
                    )

        # 根據家庭成員信息推斷人數
        if guests["adults"] is None and family_info["has_couple"]:
            guests["adults"] = 2  # 夫妻/情侶通常是2人
            logger.debug("根據家庭成員信息推斷成人數量: 2 (夫妻/情侶)")

        if guests["adults"] is None and family_info["has_parents"]:
            guests["adults"] = 2  # 父母通常是2人
            logger.debug("根據家庭成員信息推斷成人數量: 2 (父母)")

        # 檢查是否有"一家三口"、"四口之家"等表達
        for ent in doc.ents:
            if ent.label_ == "CARDINAL" and "口" in doc[ent.end : ent.end + 1].text:
                try:
                    total = int(ent.text)
                    # 假設家庭中至少有1位成人
                    if guests["adults"] is None:
                        guests["adults"] = 2  # 假設有2位成人

                    # 剩餘的是兒童
                    if guests["children"] is None:
                        guests["children"] = max(0, total - guests["adults"])

                    logger.debug(
                        f"從'口之家'表達推斷: 總人數={total}, 成人={guests['adults']}, 兒童={guests['children']}"
                    )
                    break
                except ValueError:
                    pass

        return guests

    def _extract_number_from_span(self, span) -> int | None:
        """從spaCy的span中提取數字"""
        if not self.spacy_available:
            return None

        # 首先檢查是否有數字token
        for token in span:
            if token.like_num:
                try:
                    # 處理中文數字
                    if token.text in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]:
                        chinese_nums = {
                            "一": 1,
                            "二": 2,
                            "三": 3,
                            "四": 4,
                            "五": 5,
                            "六": 6,
                            "七": 7,
                            "八": 8,
                            "九": 9,
                            "十": 10,
                        }
                        return chinese_nums.get(token.text)
                    # 處理阿拉伯數字
                    return int(token.text)
                except ValueError:
                    continue

        # 如果沒有找到數字token，嘗試從整個span文本中提取
        number_pattern = re.compile(r"\d+")
        match = number_pattern.search(span.text)
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                pass

        return None

    def _extract_guests_with_regex(self, query: str) -> dict[str, int | None]:
        """使用正則表達式從查詢中提取人數"""
        guests = {"adults": None, "children": None}

        # 提取成人數量
        for pattern in self.adult_patterns:
            match = pattern.search(query)
            if match:
                try:
                    guests["adults"] = int(match.group(1))
                    logger.debug(f"從查詢中提取到成人數量: {guests['adults']}")
                    break
                except (ValueError, IndexError):
                    continue

        # 提取兒童數量
        for pattern in self.child_patterns:
            match = pattern.search(query)
            if match:
                try:
                    guests["children"] = int(match.group(1))
                    logger.debug(f"從查詢中提取到兒童數量: {guests['children']}")
                    break
                except (ValueError, IndexError):
                    continue

        # 如果沒有明確指定兒童數量，默認為0
        if guests["children"] is None:
            guests["children"] = 0

        # 如果沒有明確指定成人數量，但有總人數，嘗試推斷成人數量
        if guests["adults"] is None:
            for pattern in self.total_patterns:
                match = pattern.search(query)
                if match:
                    try:
                        total = int(match.group(1))
                        # 如果有兒童數量，成人數量 = 總人數 - 兒童數量
                        if guests["children"] is not None:
                            guests["adults"] = max(1, total - guests["children"])
                        # 否則假設全部是成人
                        else:
                            guests["adults"] = total
                            guests["children"] = 0
                        logger.debug(f"從總人數推斷成人數量: {guests['adults']}")
                        break
                    except (ValueError, IndexError):
                        continue

        # 檢查是否有"夫妻"、"情侶"等表達
        couple_pattern = re.compile(r"夫妻|兩口子|夫婦|伴侶|情侶|一對")
        if couple_pattern.search(query) and guests["adults"] is None:
            guests["adults"] = 2
            logger.debug("從'夫妻/情侶'表達推斷成人數量: 2")

        # 檢查是否有"我和太太/老婆/先生/老公"等表達
        spouse_pattern = re.compile(r"我(?:和|與|跟)(?:太太|老婆|妻子|先生|老公|丈夫)")
        if spouse_pattern.search(query) and guests["adults"] is None:
            guests["adults"] = 2
            logger.debug("從'我和配偶'表達推斷成人數量: 2")

        # 檢查是否有"父母"等表達
        parents_pattern = re.compile(r"父母|爸媽|爸爸媽媽|家長")
        if parents_pattern.search(query) and guests["adults"] is None:
            guests["adults"] = 2
            logger.debug("從'父母'表達推斷成人數量: 2")

        # 檢查是否有"我們有X個孩子"等表達
        have_children_pattern = re.compile(r"(?:我們|我|家裡)有(\d+)(?:個|位|名)?(?:小孩|兒童|孩子)")
        match = have_children_pattern.search(query)
        if match:
            try:
                children = int(match.group(1))
                guests["children"] = children
                # 如果沒有明確指定成人數量，假設有2位成人
                if guests["adults"] is None:
                    guests["adults"] = 2
                logger.debug(f"從'有X個孩子'表達推斷: 兒童={guests['children']}, 成人={guests['adults']}")
            except ValueError:
                pass

        return guests

    async def _extract_guests_with_llm(self, query: str) -> dict[str, int | None]:
        """使用LLM從查詢中提取人數"""
        system_prompt = """
        你是一個旅館預訂系統的人數解析器。
        你的任務是從用戶的自然語言查詢中提取成人數量和兒童數量。
        
        請注意以下規則：
        1. 如果查詢中明確提到人數，請使用這些數字。
        2. 如果查詢中提到"夫妻"、"情侶"、"兩口子"等，通常表示2位成人。
        3. 如果查詢中提到"一家三口"，通常表示2位成人和1位兒童。
        4. 如果查詢中提到"父母和X個孩子"，通常表示2位成人和X位兒童。
        5. 如果查詢中提到"X口之家"或"X口家庭"，通常表示2位成人和(X-2)位兒童。
        6. 如果查詢中沒有明確提到人數，請根據上下文推斷。
        7. 如果無法推斷，請返回null。
        
        請以JSON格式返回結果，格式如下：
        {"adults": 2, "children": 0}
        
        請確保返回有效的JSON格式，不要添加其他內容。
        """

        messages = [{"role": "user", "content": f"從以下查詢中提取成人數量和兒童數量：{query}"}]
        response = await llm_service.generate_response(messages, system_prompt)

        try:
            # 清理回應，確保只包含JSON
            response = response.strip()
            # 如果回應包含多行，嘗試找到JSON部分
            if "\n" in response:
                for line in response.split("\n"):
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        response = line
                        break

            # 使用正則表達式提取JSON
            json_pattern = re.compile(r"{.*?}", re.DOTALL)
            match = json_pattern.search(response)
            if match:
                import orjson

                json_str = match.group(0)
                # 進一步清理JSON字符串
                json_str = json_str.replace("'", '"')  # 將單引號替換為雙引號
                guests = orjson.loads(json_str)
                return guests
            # 如果無法找到JSON，嘗試手動解析
            adults_pattern = re.compile(r'"adults":\s*(\d+)')
            children_pattern = re.compile(r'"children":\s*(\d+)')

            adults_match = adults_pattern.search(response)
            children_match = children_pattern.search(response)

            adults = int(adults_match.group(1)) if adults_match else None
            children = int(children_match.group(1)) if children_match else None

            return {"adults": adults, "children": children}
        except Exception as e:
            logger.error(f"LLM人數解析失敗: {e!s}")
            logger.debug(f"LLM回應: {response}")

        return {"adults": None, "children": None}

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的人數信息"""
        logger.info(f"解析查詢中的人數信息: {query}")

        # 首先使用同步方法解析
        guests = self.parse(query)

        # 如果正則表達式和spaCy無法解析，嘗試使用LLM解析
        if guests["adults"] is None or guests["children"] is None:
            try:
                llm_guests = await self._extract_guests_with_llm(query)

                # 合併結果，優先使用已有的解析結果
                if guests["adults"] is None and llm_guests["adults"] is not None:
                    guests["adults"] = llm_guests["adults"]
                    logger.debug(f"使用LLM解析到成人數量: {guests['adults']}")

                if guests["children"] is None and llm_guests["children"] is not None:
                    guests["children"] = llm_guests["children"]
                    logger.debug(f"使用LLM解析到兒童數量: {guests['children']}")
            except Exception as e:
                logger.error(f"LLM解析過程中發生錯誤: {e!s}")

        # 如果仍然無法解析，設置默認值
        if guests["adults"] is None:
            guests["adults"] = 2  # 默認2位成人
            logger.info("無法解析成人數量，使用默認值: 2")

        if guests["children"] is None:
            guests["children"] = 0  # 默認0位兒童
            logger.info("無法解析兒童數量，使用默認值: 0")

        return {"guests": guests}


# 創建人數解析子Agent實例
guest_parser_agent = GuestParserAgent()
