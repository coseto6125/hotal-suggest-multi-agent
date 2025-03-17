"""
日期解析子Agent，專門負責解析查詢中的旅遊日期
"""

import re
from datetime import datetime, timedelta
from typing import Any, ClassVar

import spacy
from loguru import logger
from spacy.matcher import Matcher

from src.agents.base.base_agent import BaseAgent
from src.utils.nlp_utils import get_shared_spacy_model


class DateParserAgent(BaseAgent):
    """日期解析子Agent"""

    # 靜態共享的spaCy模型
    _shared_nlp: ClassVar[spacy.Language | None] = None

    def __init__(self):
        """初始化日期解析子Agent"""
        super().__init__("DateParserAgent")
        # 日期正則表達式模式
        self.date_patterns = [
            # YYYY-MM-DD 或 YYYY/MM/DD
            re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"),
            # MM-DD 或 MM/DD
            re.compile(r"(\d{1,2})[/-](\d{1,2})"),
            # 中文日期格式：X月X日
            re.compile(r"(\d{1,2})月(\d{1,2})日"),
            # 中文日期格式：X月X號
            re.compile(r"(\d{1,2})月(\d{1,2})號"),
        ]
        self.err_result = {
            "error": "日期解析失敗",
            "err_msg": "不好意思，似乎無法確認您的入住日期，麻煩您加上月/日再提供一次。",
        }

        # 初始化spaCy模型
        self.spacy_available = False
        try:
            # 嘗試獲取共享的spaCy模型
            self.nlp = get_shared_spacy_model("zh_core_web_md")
            self.spacy_available = True
            logger.info("成功載入spaCy中文模型用於日期解析")

            # 設置spaCy匹配器
            self.matcher = Matcher(self.nlp.vocab)

            # 添加日期匹配模式
            self.matcher.add(
                "DATE_PATTERN",
                [
                    # X月X日
                    [
                        {"LIKE_NUM": True},
                        {"TEXT": "月"},
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["日", "號"]}},
                    ],
                    # X月X日至Y月Z日
                    [
                        {"LIKE_NUM": True},
                        {"TEXT": "月"},
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["日", "號"]}},
                        {"TEXT": {"IN": ["至", "到", "-", "~"]}},
                        {"LIKE_NUM": True},
                        {"TEXT": "月"},
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["日", "號"]}},
                    ],
                    # X日至Y日
                    [
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["日", "號"]}},
                        {"TEXT": {"IN": ["至", "到", "-", "~"]}},
                        {"LIKE_NUM": True},
                        {"TEXT": {"IN": ["日", "號"]}},
                    ],
                    # 今天/明天/後天
                    [{"TEXT": {"IN": ["今天", "今晚", "明天", "後天", "大後天"]}}],
                    # 這週末/下週末
                    [{"TEXT": {"IN": ["這", "這個"]}}, {"TEXT": "週末"}],
                    [{"TEXT": {"IN": ["下", "下個"]}}, {"TEXT": "週末"}],
                    # 下週一/二/三...
                    [
                        {"TEXT": {"IN": ["下", "下個"]}},
                        {"TEXT": {"IN": ["週", "星期"]}},
                        {"TEXT": {"IN": ["一", "二", "三", "四", "五", "六", "日", "天"]}},
                    ],
                ],
            )

        except Exception as e:
            logger.warning(f"無法載入spaCy中文模型用於日期解析: {e!s}，將使用正則表達式解析")
            self.spacy_available = False

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的旅遊日期"""
        query = state.get("query", "")
        context = state.get("context", {})

        logger.debug(f"[{self.name}] 開始解析日期")
        try:
            # 首先嘗試使用spaCy解析日期
            dates = {}
            if self.spacy_available:
                dates = self._extract_dates_with_spacy(query)
                logger.debug(f"[{self.name}] spaCy解析結果: {dates}")

            # 如果spaCy無法解析，嘗試使用正則表達式
            if not dates.get("check_in") or not dates.get("check_out"):
                regex_dates = self._extract_dates_with_regex(query)
                logger.debug(f"[{self.name}] 正則表達式解析結果: {regex_dates}")

                # 合併結果，優先使用已解析的結果
                if not dates.get("check_in") and regex_dates.get("check_in"):
                    dates["check_in"] = regex_dates["check_in"]
                if not dates.get("check_out") and regex_dates.get("check_out"):
                    dates["check_out"] = regex_dates["check_out"]

            # 如果仍然無法解析，嘗試根據上下文推斷
            if not dates.get("check_in") or not dates.get("check_out"):
                inferred_dates = self._infer_dates(query)
                logger.debug(f"[{self.name}] 推斷日期結果: {inferred_dates}")

                # 合併結果，優先使用已解析的結果
                if not dates.get("check_in") and inferred_dates.get("check_in"):
                    dates["check_in"] = inferred_dates["check_in"]
                if not dates.get("check_out") and inferred_dates.get("check_out"):
                    dates["check_out"] = inferred_dates["check_out"]

            # 驗證日期的有效性
            self._validate_dates(dates)

            logger.info(
                f"[{self.name}] 解析結果：入住 {dates.get('check_in', '未知')}，退房 {dates.get('check_out', '未知')}"
            )

            # 如果都無法解析，返回空值
            if not dates.get("check_in") and not dates.get("check_out"):
                return self.err_result

            # 確保退房日期在入住日期之後
            if dates.get("check_in") and dates.get("check_out"):
                check_in_date = datetime.strptime(dates["check_in"], "%Y-%m-%d")
                checkout_date = datetime.strptime(dates["check_out"], "%Y-%m-%d")
                if check_in_date >= checkout_date:
                    # 如果退房日期不在入住日期之後，設置為入住日期後一天
                    checkout_date = check_in_date + timedelta(days=1)
                    dates["check_out"] = checkout_date.strftime("%Y-%m-%d")
                    logger.warning(f"[{self.name}] 退房日期不在入住日期之後，自動調整為：{dates['check_out']}")

            return dates

        except Exception as e:
            logger.error(f"[{self.name}] 日期解析失敗: {e}")

            return self.err_result

    def _extract_dates_with_spacy(self, query: str) -> dict[str, str]:
        """使用spaCy從查詢中提取日期"""
        if not self.spacy_available:
            return {"check_in": None, "check_out": None}

        dates = {"check_in": None, "check_out": None}
        all_dates = []
        current_year = datetime.now().year
        today = datetime.now()

        # 解析文本
        doc = self.nlp(query)

        # 首先檢查是否有DATE實體
        for ent in doc.ents:
            if ent.label_ == "DATE":
                logger.debug(f"spaCy識別到DATE實體: {ent.text}")
                # 嘗試解析日期實體
                date_str = self._parse_date_entity(ent.text, current_year, today)
                if date_str:
                    all_dates.append(date_str)

        # 使用匹配器查找匹配項
        matches = self.matcher(doc)
        today_str = today.strftime("%Y-%m-%d")

        for _, start, end in matches:
            text = doc[start:end].text
            logger.debug(f"spaCy匹配到日期表達: {text}")
            
            match text:
                case t if any(m in t for m in "至到-~"):
                    date_range = self._parse_date_range(text, current_year)
                    if date_range and len(date_range) == 2:
                        dates["check_in"], dates["check_out"] = date_range
                        return dates
                
                case t if "月" in t and ("日" in t or "號" in t):
                    if date_str := self._parse_single_date(text, current_year):
                        all_dates.append(date_str)
                
                case "今天" | "今晚":
                    all_dates.append(today_str)
                
                case "明天":
                    all_dates.append((today + timedelta(days=1)).strftime("%Y-%m-%d"))
                
                case "後天":
                    all_dates.append((today + timedelta(days=2)).strftime("%Y-%m-%d"))
                
                case "大後天":
                    all_dates.append((today + timedelta(days=3)).strftime("%Y-%m-%d"))
                
                case t if "週末" in t or "周末" in t:
                    is_next = "下" in t or "下個" in t
                    offset = 7 if is_next else 0
                    days_to_sat = (5 - today.weekday()) % 7 + offset
                    sat = today + timedelta(days=days_to_sat)
                    all_dates.extend([
                        sat.strftime("%Y-%m-%d"),
                        (sat + timedelta(days=1)).strftime("%Y-%m-%d")
                    ])
                
                case t if any(m in t for m in ["下週", "下星期", "下周"]):
                    for day, offset in {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}.items():
                        if day in t:
                            days_to_mon = (7 - today.weekday()) % 7 or 7
                            next_day = today + timedelta(days=days_to_mon + offset)
                            all_dates.append(next_day.strftime("%Y-%m-%d"))
                            break

        # 如果找到至少兩個日期，假設第一個是入住日期，第二個是退房日期
        if len(all_dates) >= 2:
            # 排序日期，確保入住日期在前
            all_dates.sort()
            dates["check_in"] = all_dates[0]
            dates["check_out"] = all_dates[1]
        elif len(all_dates) == 1:
            # 如果只找到一個日期，假設是入住日期，退房日期為入住日期後的第二天
            dates["check_in"] = all_dates[0]
            check_in_date = datetime.strptime(all_dates[0], "%Y-%m-%d")
            check_out_date = check_in_date + timedelta(days=1)
            dates["check_out"] = check_out_date.strftime("%Y-%m-%d")

        return dates

    def _parse_date_entity(self, text: str, current_year: int, today: datetime) -> str | None:
        """解析日期實體文本"""
        try:
            # 處理常見的日期表達
            if text in ["今天", "今日", "今晚"]:
                return today.strftime("%Y-%m-%d")
            if text in ["明天", "明日"]:
                return (today + timedelta(days=1)).strftime("%Y-%m-%d")
            if text in ["後天", "後日"]:
                return (today + timedelta(days=2)).strftime("%Y-%m-%d")
            if text == "大後天":
                return (today + timedelta(days=3)).strftime("%Y-%m-%d")

            # 處理"X月X日"格式
            month_day_pattern = re.compile(r"(\d{1,2})月(\d{1,2})(?:日|號)")
            match = month_day_pattern.search(text)
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                return f"{current_year:04d}-{month:02d}-{day:02d}"

            return None
        except (ValueError, IndexError):
            return None

    def _parse_date_range(self, text: str, current_year: int) -> list[str] | None:
        """解析日期範圍表達，如"5月1日至5月3日"或"5月1日至3日" """
        try:
            # 處理"X月X日至Y月Z日"格式
            full_range_pattern = re.compile(r"(\d{1,2})月(\d{1,2})(?:日|號)(?:至|到|-|~)(\d{1,2})月(\d{1,2})(?:日|號)")
            match = full_range_pattern.search(text)
            if match:
                month1, day1, month2, day2 = (
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                    int(match.group(4)),
                )
                date1 = f"{current_year:04d}-{month1:02d}-{day1:02d}"
                date2 = f"{current_year:04d}-{month2:02d}-{day2:02d}"
                return [date1, date2]

            # 處理"X月X日至Z日"格式（同月不同日）
            same_month_pattern = re.compile(r"(\d{1,2})月(\d{1,2})(?:日|號)(?:至|到|-|~)(\d{1,2})(?:日|號)")
            match = same_month_pattern.search(text)
            if match:
                month, day1, day2 = int(match.group(1)), int(match.group(2)), int(match.group(3))
                date1 = f"{current_year:04d}-{month:02d}-{day1:02d}"
                date2 = f"{current_year:04d}-{month:02d}-{day2:02d}"
                return [date1, date2]

            return None
        except (ValueError, IndexError):
            return None

    def _parse_single_date(self, text: str, current_year: int) -> str | None:
        """解析單個日期表達，如"5月1日" """
        try:
            # 處理"X月X日"格式
            pattern = re.compile(r"(\d{1,2})月(\d{1,2})(?:日|號)")
            match = pattern.search(text)
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                return f"{current_year:04d}-{month:02d}-{day:02d}"

            return None
        except (ValueError, IndexError):
            return None

    def _extract_dates_with_regex(self, query: str) -> dict[str, str]:
        """使用正則表達式從查詢中提取日期"""
        dates = {"check_in": None, "check_out": None}

        # 提取所有可能的日期
        all_dates = []
        current_year = datetime.now().year

        for pattern in self.date_patterns:
            matches = pattern.findall(query)
            for match in matches:
                try:
                    if len(match) == 3:  # YYYY-MM-DD
                        year, month, day = int(match[0]), int(match[1]), int(match[2])
                        date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    elif len(match) == 2:  # MM-DD 或 中文日期
                        month, day = int(match[0]), int(match[1])
                        date_str = f"{current_year:04d}-{month:02d}-{day:02d}"

                    # 驗證日期有效性
                    datetime.strptime(date_str, "%Y-%m-%d")
                    all_dates.append(date_str)
                except (ValueError, IndexError):
                    continue

        # 如果找到至少兩個日期，假設第一個是入住日期，第二個是退房日期
        if len(all_dates) >= 2:
            # 排序日期，確保入住日期在前
            all_dates.sort()
            dates["check_in"] = all_dates[0]
            dates["check_out"] = all_dates[1]
        elif len(all_dates) == 1:
            # 如果只找到一個日期，假設是入住日期，退房日期為入住日期後的第二天
            dates["check_in"] = all_dates[0]
            check_in_date = datetime.strptime(all_dates[0], "%Y-%m-%d")
            check_out_date = check_in_date + timedelta(days=1)
            dates["check_out"] = check_out_date.strftime("%Y-%m-%d")

        return dates

    def _infer_dates(self, query: str) -> dict[str, str]:
        """根據查詢內容推斷日期"""
        dates = {"check_in": None, "check_out": None}
        today = datetime.now()

        # 檢查是否包含特定關鍵詞
        if "今天" in query or "今晚" in query:
            dates["check_in"] = today.strftime("%Y-%m-%d")
            dates["check_out"] = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "明天" in query:
            tomorrow = today + timedelta(days=1)
            dates["check_in"] = tomorrow.strftime("%Y-%m-%d")
            dates["check_out"] = (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "後天" in query:
            day_after_tomorrow = today + timedelta(days=2)
            dates["check_in"] = day_after_tomorrow.strftime("%Y-%m-%d")
            dates["check_out"] = (day_after_tomorrow + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "這週末" in query or "這個週末" in query:
            # 計算到本週六的天數
            days_until_saturday = (5 - today.weekday()) % 7
            saturday = today if days_until_saturday == 0 else today + timedelta(days=days_until_saturday)
            sunday = saturday + timedelta(days=1)

            dates["check_in"] = saturday.strftime("%Y-%m-%d")
            dates["check_out"] = sunday.strftime("%Y-%m-%d")
        elif "下週" in query or "下個週" in query:
            # 計算到下週一的天數
            days_until_next_monday = (7 - today.weekday()) % 7
            if days_until_next_monday == 0:  # 如果今天是週一
                days_until_next_monday = 7

            next_monday = today + timedelta(days=days_until_next_monday)
            next_wednesday = next_monday + timedelta(days=2)

            dates["check_in"] = next_monday.strftime("%Y-%m-%d")
            dates["check_out"] = next_wednesday.strftime("%Y-%m-%d")

        return dates

    def _validate_dates(self, dates: dict[str, str]) -> None:
        """驗證日期的有效性"""
        today = datetime.now().date()

        # 檢查入住日期
        if dates.get("check_in"):
            try:
                check_in_date = datetime.strptime(dates["check_in"], "%Y-%m-%d").date()

                # 入住日期不能早於今天
                if check_in_date < today:
                    logger.warning(f"入住日期 {dates['check_in']} 早於今天，設置為今天")
                    dates["check_in"] = today.strftime("%Y-%m-%d")
            except ValueError:
                logger.error(f"無效的入住日期格式: {dates['check_in']}")
                dates["check_in"] = None

        # 檢查退房日期
        if dates.get("check_out"):
            try:
                check_out_date = datetime.strptime(dates["check_out"], "%Y-%m-%d").date()

                # 如果有入住日期，退房日期必須晚於入住日期
                if dates.get("check_in"):
                    check_in_date = datetime.strptime(dates["check_in"], "%Y-%m-%d").date()
                    if check_out_date <= check_in_date:
                        logger.warning(
                            f"退房日期 {dates['check_out']} 不晚於入住日期 {dates['check_in']}，設置為入住日期後一天"
                        )
                        dates["check_out"] = (check_in_date + timedelta(days=1)).strftime("%Y-%m-%d")
            except ValueError:
                logger.error(f"無效的退房日期格式: {dates['check_out']}")
                dates["check_out"] = None
