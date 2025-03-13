from typing import Any

from pydantic import BaseModel


class County(BaseModel):
    """縣市模型"""

    id: str
    name: str
    # TODO: 定義縣市數據模型的其他欄位


class District(BaseModel):
    """鄉鎮區模型"""

    id: str
    name: str
    county_id: str
    # TODO: 定義鄉鎮區數據模型的其他欄位


class Hotel(BaseModel):
    """旅館模型"""

    id: str
    name: str
    address: str
    rating: float | None = None
    facilities: list[str] = []
    room_types: list[dict[str, Any]] = []
    # TODO: 定義旅館數據模型的其他欄位


class Place(BaseModel):
    """景點模型"""

    id: str
    name: str
    address: str
    types: list[str] = []
    rating: float | None = None
    location: dict[str, float]
    # TODO: 定義景點數據模型的其他欄位
