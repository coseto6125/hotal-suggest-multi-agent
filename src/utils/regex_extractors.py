"""
正則表達式提取工具

提供通用的正則表達式提取函數，用於減少重複代碼
"""

import re
from typing import Pattern


def extract_with_patterns(text: str, patterns: list[Pattern]) -> str | None:
    """
    使用多個正則表達式模式從文本中提取信息

    Args:
        text: 要提取信息的文本
        patterns: 正則表達式模式列表

    Returns:
        提取的信息，如果沒有找到則返回 None
    """
    if not text:
        return None

    for pattern in patterns:
        match = pattern.search(text)
        if match:
            # 提取第一個捕獲組
            return match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()

    return None


def extract_all_with_patterns(text: str, patterns: list[Pattern]) -> list[str]:
    """
    使用多個正則表達式模式從文本中提取所有匹配的信息

    Args:
        text: 要提取信息的文本
        patterns: 正則表達式模式列表

    Returns:
        提取的信息列表
    """
    if not text:
        return []

    results = []
    for pattern in patterns:
        matches = pattern.findall(text)
        for match in matches:
            if isinstance(match, tuple) and len(match) > 0:
                results.append(match[0].strip())
            elif isinstance(match, str):
                results.append(match.strip())

    return results


def extract_number(text: str) -> int | None:
    """
    從文本中提取數字

    Args:
        text: 要提取數字的文本

    Returns:
        提取的數字，如果沒有找到則返回 None
    """
    if not text:
        return None

    # 移除千分位分隔符
    text = text.replace(",", "")

    # 提取數字
    number_pattern = re.compile(r"(\d+)")
    match = number_pattern.search(text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None

    return None


def extract_date_components(text: str) -> dict[str, int | None]:
    """
    從文本中提取日期元素 (年、月、日)

    Args:
        text: 要提取日期元素的文本

    Returns:
        包含年、月、日的字典，如果沒有找到則相應元素為 None
    """
    date_components = {"year": None, "month": None, "day": None}

    # 年月日模式
    ymd_pattern = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")
    md_pattern = re.compile(r"(\d{1,2})[/-](\d{1,2})")
    zh_md_pattern = re.compile(r"(\d{1,2})月(\d{1,2})(?:日|號)")

    # 提取年月日
    ymd_match = ymd_pattern.search(text)
    if ymd_match:
        date_components["year"] = int(ymd_match.group(1))
        date_components["month"] = int(ymd_match.group(2))
        date_components["day"] = int(ymd_match.group(3))
        return date_components

    # 提取月日
    md_match = md_pattern.search(text)
    if md_match:
        date_components["month"] = int(md_match.group(1))
        date_components["day"] = int(md_match.group(2))
        return date_components

    # 提取中文月日
    zh_md_match = zh_md_pattern.search(text)
    if zh_md_match:
        date_components["month"] = int(zh_md_match.group(1))
        date_components["day"] = int(zh_md_match.group(2))
        return date_components

    return date_components


def extract_price_range(text: str) -> dict[str, int | None]:
    """
    從文本中提取價格範圍

    Args:
        text: 要提取價格範圍的文本

    Returns:
        包含最低價和最高價的字典
    """
    price_range = {"min": None, "max": None}

    # 範圍模式
    range_pattern = re.compile(r"(\d+(?:,\d+)?)\s*(?:-|~|到)\s*(\d+(?:,\d+)?)")

    # 最低價模式
    min_pattern = re.compile(r"(?:最低|至少|起碼|含括|下限|最少)\s*(\d+(?:,\d+)?)")

    # 最高價模式
    max_pattern = re.compile(r"(?:最高|最多|不超過|上限)\s*(\d+(?:,\d+)?)")

    # 單一價格模式
    single_pattern = re.compile(r"(\d+(?:,\d+)?)\s*(?:元|塊|NT\$|台幣|TWD|NTD|新台幣)(?:左右|上下)?")

    # 提取價格範圍
    range_match = range_pattern.search(text)
    if range_match:
        price_range["min"] = int(range_match.group(1).replace(",", ""))
        price_range["max"] = int(range_match.group(2).replace(",", ""))
        return price_range

    # 提取最低價
    min_match = min_pattern.search(text)
    if min_match:
        price_range["min"] = int(min_match.group(1).replace(",", ""))

    # 提取最高價
    max_match = max_pattern.search(text)
    if max_match:
        price_range["max"] = int(max_match.group(1).replace(",", ""))

    # 如果只找到單一價格，將其設置為參考價格 (min - 20%, max + 20%)
    if not price_range["min"] and not price_range["max"]:
        single_match = single_pattern.search(text)
        if single_match:
            price = int(single_match.group(1).replace(",", ""))
            price_range["min"] = int(price * 0.8)
            price_range["max"] = int(price * 1.2)

    return price_range


def extract_boolean_presence(text: str, positive_patterns: list[str], negative_patterns: list[str]) -> bool | None:
    """
    從文本中提取布爾值是否存在 (例如：是否有早餐)

    Args:
        text: 要提取布爾值的文本
        positive_patterns: 表示存在的模式列表
        negative_patterns: 表示不存在的模式列表

    Returns:
        布爾值，如果找到積極模式則為 True，如果找到消極模式則為 False，如果都沒有找到則為 None
    """
    if not text:
        return None

    # 檢查積極模式
    for pattern in positive_patterns:
        if re.search(pattern, text):
            return True

    # 檢查消極模式
    for pattern in negative_patterns:
        if re.search(pattern, text):
            return False

    return None
