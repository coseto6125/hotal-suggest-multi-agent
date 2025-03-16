"""
數據模型，定義系統中使用的數據結構
"""

from pydantic import BaseModel, Field


# 基礎參數模型
class County(BaseModel):
    """縣市模型"""

    id: str
    name: str


class District(BaseModel):
    """鄉鎮區模型"""

    id: str
    name: str
    county_id: str


class HotelType(BaseModel):
    """旅館類型模型"""

    id: str
    name: str


class HotelFacility(BaseModel):
    """飯店設施模型"""

    id: str
    name: str


class RoomFacility(BaseModel):
    """房間備品模型"""

    id: str
    name: str


class BedType(BaseModel):
    """房間床型模型"""

    id: str
    name: str


# 旅館相關模型
class HotelLocation(BaseModel):
    """旅館位置模型"""

    latitude: float
    longitude: float


class HotelBasicInfo(BaseModel):
    """旅館基本信息模型"""

    id: str
    name: str
    address: str
    location: HotelLocation | None = None
    rating: float | None = None
    type_id: str | None = None
    type_name: str | None = None


class RoomType(BaseModel):
    """房間類型模型"""

    id: str
    name: str
    price: float
    bed_type_id: str | None = None
    bed_type_name: str | None = None
    facilities: list[RoomFacility] | None = None


class HotelDetail(BaseModel):
    """旅館詳情模型"""

    id: str
    name: str
    address: str
    description: str | None = None
    location: HotelLocation | None = None
    rating: float | None = None
    type_id: str | None = None
    type_name: str | None = None
    facilities: list[HotelFacility] | None = None
    room_types: list[RoomType] | None = None
    images: list[str] | None = None


class Plan(BaseModel):
    """訂購方案模型"""

    id: str
    name: str
    hotel_id: str
    hotel_name: str
    price: float
    description: str | None = None


# 周邊地標相關模型
class POILocation(BaseModel):
    """地標位置模型"""

    latitude: float
    longitude: float


class POIDisplayName(BaseModel):
    """地標顯示名稱模型"""

    text: str


class POI(BaseModel):
    """地標模型"""

    types: list[str]
    formattedAddress: str
    location: POILocation
    rating: float | None = None
    displayName: POIDisplayName


class POISearchResult(BaseModel):
    """地標搜尋結果模型"""

    surroundings_map_images: list[str]
    places: list[POI]


# 聊天相關模型
class ChatMessage(BaseModel):
    """聊天消息模型"""

    role: str = Field(..., description="消息角色，'user' 或 'assistant'")
    content: str = Field(..., description="消息內容")
    timestamp: float | None = None


class ChatRequest(BaseModel):
    """聊天請求模型"""

    message: str = Field(..., description="用戶消息")
    conversation_id: str | None = Field(None, description="對話ID，首次對話可為空")


class ChatResponse(BaseModel):
    """聊天響應模型"""

    message: str = Field(..., description="助手回覆")
    conversation_id: str = Field(..., description="對話ID")
    is_complete: bool = Field(..., description="是否為完整回覆")


class StreamChatResponse(BaseModel):
    """流式聊天響應模型"""

    message_chunk: str = Field(..., description="助手回覆片段")
    conversation_id: str = Field(..., description="對話ID")
    is_complete: bool = Field(..., description="是否為完整回覆")
    stage: str | None = Field(None, description="處理階段，如'parse_query', 'geo_parse', 'search_hotels'等")
    geo_data: dict | None = Field(None, description="地理位置數據")
    error: str | None = Field(None, description="錯誤信息")
    is_collapsible: bool | None = Field(None, description="是否可摺疊")

    class Config:
        extra = "allow"  # 允許額外的屬性
