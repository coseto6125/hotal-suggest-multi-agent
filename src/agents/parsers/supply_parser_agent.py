"""
備品搜尋子Agent，專門負責解析查詢中的房間備品名稱
"""

import re
from typing import Any

from loguru import logger

from src.agents.base.base_sub_agent import BaseSubAgent


class SupplyParserAgent(BaseSubAgent):
    """備品搜尋子Agent"""

    def __init__(self):
        """初始化備品搜尋子Agent"""
        super().__init__("SupplyParserAgent")
        # 常見備品關鍵詞
        self.common_supplies = [
            "牙刷",
            "牙膏",
            "梳子",
            "洗髮精",
            "沐浴乳",
            "香皂",
            "洗面乳",
            "乳液",
            "化妝棉",
            "棉花棒",
            "刮鬍刀",
            "浴帽",
            "拖鞋",
            "浴袍",
            "毛巾",
            "浴巾",
            "吹風機",
            "熨斗",
            "衣架",
            "保險箱",
            "冰箱",
            "電視",
            "電熱水壺",
            "咖啡機",
            "茶包",
            "礦泉水",
            "杯子",
            "馬克杯",
            "開瓶器",
            "雨傘",
            "針線包",
            "鬧鐘",
            "充電器",
            "轉接頭",
            "延長線",
            "衛生紙",
            "面紙",
            "濕紙巾",
            "垃圾袋",
            "洗衣袋",
            "洗衣粉",
            "洗衣精",
            "衣物柔軟精",
            "熨衣板",
            "嬰兒床",
            "嬰兒浴盆",
            "尿布",
            "奶瓶",
            "奶瓶消毒器",
            "嬰兒食品",
            "嬰兒車",
            "兒童椅",
            "兒童餐具",
            "兒童書籍",
            "兒童玩具",
            "遊戲機",
            "DVD播放機",
            "藍牙音箱",
            "書桌",
            "辦公椅",
            "文具",
            "筆記本",
            "筆",
            "便條紙",
            "信封",
            "印表機",
            "傳真機",
            "掃描器",
            "影印機",
            "投影機",
            "螢幕",
            "鍵盤",
            "滑鼠",
            "耳機",
            "麥克風",
            "攝影機",
            "三腳架",
            "相機",
            "記憶卡",
            "充電寶",
            "行動電源",
            "手機支架",
            "平板支架",
            "筆電支架",
            "筆電包",
            "背包",
            "行李箱",
            "行李秤",
            "旅行轉接頭",
            "旅行套裝",
            "旅行袋",
            "旅行枕",
            "眼罩",
            "耳塞",
            "睡衣",
            "睡袍",
            "睡帽",
            "睡襪",
            "保溫杯",
            "保溫壺",
            "保鮮盒",
            "保鮮袋",
            "保鮮膜",
            "餐具",
            "筷子",
            "湯匙",
            "叉子",
            "刀子",
            "碗",
            "盤子",
            "鍋子",
            "平底鍋",
            "電鍋",
            "微波爐",
            "烤箱",
            "烤麵包機",
            "榨汁機",
            "攪拌機",
            "電磁爐",
            "瓦斯爐",
            "抽油煙機",
            "洗碗機",
            "洗衣機",
            "烘衣機",
            "吸塵器",
            "掃地機器人",
            "拖把",
            "掃把",
            "畚箕",
            "抹布",
            "海綿",
            "洗碗精",
            "洗碗布",
            "洗碗海綿",
            "洗碗刷",
            "洗衣籃",
            "衣架",
            "衣櫃",
            "衣櫥",
            "衣帽架",
            "鞋架",
            "鞋櫃",
            "鞋刷",
            "鞋油",
            "鞋拔",
            "鞋帶",
            "鞋墊",
            "鞋撐",
            "鞋袋",
            "鞋盒",
            "鞋套",
        ]

        # 備品搜尋模式正則表達式
        self.supply_search_patterns = [
            re.compile(
                r"(?:找|搜尋|搜索|查詢|查找|尋找|查|搜|尋)(?:有|提供|附帶|帶有|包含|具有|具備|配有|配備|設有|設備|備有|備)(?:的)?(.+?)(?:的)?(?:旅館|酒店|飯店|民宿|住宿|房間|房)"
            ),
            re.compile(
                r"(?:旅館|酒店|飯店|民宿|住宿|房間|房)(?:有|提供|附帶|帶有|包含|具有|具備|配有|配備|設有|設備|備有|備)(?:的)?(.+?)"
            ),
            re.compile(
                r"(?:有|提供|附帶|帶有|包含|具有|具備|配有|配備|設有|設備|備有|備)(.+?)(?:的)?(?:旅館|酒店|飯店|民宿|住宿|房間|房)"
            ),
            re.compile(
                r"(?:需要|想要|要有|要提供|要附帶|要帶有|要包含|要具有|要具備|要配有|要配備|要設有|要設備|要備有|要備)(.+?)(?:的)?(?:旅館|酒店|飯店|民宿|住宿|房間|房)"
            ),
        ]

    async def _process_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """處理查詢中的房間備品名稱"""
        logger.info(f"解析查詢中的房間備品名稱: {query}")

        # 使用正則表達式解析備品名稱
        supply_name = self._extract_supply_with_regex(query)

        # 檢查是否是備品搜尋模式
        is_supply_search = bool(supply_name)

        return {"supply_name": supply_name, "is_supply_search": is_supply_search}

    def _extract_supply_with_regex(self, query: str) -> str:
        """使用正則表達式從查詢中提取備品名稱"""
        # 嘗試使用備品搜尋模式正則表達式提取備品名稱
        for pattern in self.supply_search_patterns:
            match = pattern.search(query)
            if match:
                supply_text = match.group(1).strip()
                logger.debug(f"從查詢中提取到備品文本: {supply_text}")

                # 檢查提取的文本是否包含常見備品
                for supply in self.common_supplies:
                    if supply in supply_text:
                        logger.info(f"從查詢中提取到備品名稱: {supply}")
                        return supply

                # 如果沒有匹配到常見備品，但文本較短，可能是備品名稱
                if len(supply_text) <= 5:
                    logger.info(f"從查詢中提取到可能的備品名稱: {supply_text}")
                    return supply_text

        # 直接檢查查詢中是否包含常見備品
        for supply in self.common_supplies:
            if supply in query:
                logger.info(f"從查詢中直接匹配到備品名稱: {supply}")
                return supply

        return ""


# 創建備品搜尋子Agent實例
supply_parser_agent = SupplyParserAgent()
