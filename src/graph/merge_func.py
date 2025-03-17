# ========== 狀態合併工具函數 ==========
import copy
from typing import Any


class MergeFunc:
    """狀態合併相關工具函數集合"""

    @staticmethod
    def dict_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        """合併兩個字典"""
        result = dict1.copy()
        result.update(dict2)
        return result

    @staticmethod
    def merge_list_top3(list1: list[Any], list2: list[Any]) -> list[Any]:
        """合併兩個列表，只保留前3個"""
        result = list1.copy()
        result.extend(list2)
        return result[:3]

    @staticmethod
    def response(response1: dict[str, Any] | None, response2: dict[str, Any] | None) -> dict[str, Any] | None:
        """合併兩個回應對象，如果有衝突，優先使用第二個回應"""
        if response1 is None:
            return response2
        if response2 is None:
            return response1
        result = copy.deepcopy(response1)
        result.update(response2)
        return result

    @staticmethod
    def text_response(text1: str, text2: str) -> str:
        """合併兩個文本回應，使用換行符分隔"""
        if not text1:
            return text2
        if not text2:
            return text1
        return f"{text1}\n{text2}"

    @staticmethod
    def hotel_results(list1: list[dict[str, Any]], list2: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """合併旅館搜索結果，去除重複項"""
        result = list1.copy()
        existing_ids = {item.get("id") for item in result if "id" in item}

        for item in list2:
            if "id" in item and item["id"] not in existing_ids:
                result.append(item)
                existing_ids.add(item["id"])
        return result

    @staticmethod
    def plan_results(list1: list[dict[str, Any]], list2: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """合併方案搜索結果，去除重複項"""
        result = list1.copy()
        existing_ids = {item.get("plan_id") for item in result if "plan_id" in item}

        for item in list2:
            if "plan_id" in item and item["plan_id"] not in existing_ids:
                result.append(item)
                existing_ids.add(item["plan_id"])
        return result

    @staticmethod
    def unique_ids(list1: list[int], list2: list[int]) -> list[int]:
        """合併兩個ID列表，去除重複項"""
        return list(set(list1 + list2))

    @staticmethod
    def keep_first(any1: str | float | bool | None, any2: str | float | bool | None) -> str | int | float | bool | None:
        """合併兩個任意類型，保留第一個非None值"""
        return any1 if any1 is not None else any2

    @staticmethod
    def keep_last(any1: str | float | bool | None, any2: str | float | bool | None) -> str | int | float | bool | None:
        """合併兩個字符串，優先採用非空值"""
        return any2 if any2 is not None else any1

    @staticmethod
    def max_int(n1: int | None, n2: int | None) -> int | None:
        """合併兩個整數，取較大值"""
        if n1 is None:
            return n2
        if n2 is None:
            return n1
        return max(n1, n2)

    @staticmethod
    def min_int(n1: int | None, n2: int | None) -> int | None:
        """合併兩個整數，取較小值"""
        if n1 is None:
            return n2
        if n2 is None:
            return n1
        return min(n1, n2)

    @staticmethod
    def bool_or(b1: bool, b2: bool) -> bool:
        """合併兩個布爾值，有任一為True則結果為True"""
        return b1 or b2

    @staticmethod
    def bool_and(b1: bool, b2: bool) -> bool:
        """合併兩個布爾值，兩者都為True才結果為True"""
        return b1 and b2

    @staticmethod
    def keep_not_none(any1: str, any2: str) -> str:
        """合併兩個字符串，保留非空值"""
        return any1 or any2
